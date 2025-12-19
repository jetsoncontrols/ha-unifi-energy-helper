"""Support for UniFi Energy Helper energy sensors."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SECONDS_TO_HOURS, UNIFI_DOMAIN, WATTS_TO_KILOWATTS

_LOGGER = logging.getLogger(__name__)


def _is_poe_power_entity(entry: er.RegistryEntry) -> bool:
    """Check if an entity registry entry is a UniFi PoE power sensor."""
    if not (
        entry.platform == UNIFI_DOMAIN
        and entry.entity_id.startswith("sensor.")
        and entry.device_id
        and entry.original_device_class == SensorDeviceClass.POWER
        and entry.unit_of_measurement == UnitOfPower.WATT
        and entry.disabled_by is None
    ):
        return False

    # Check if this is likely a PoE port power sensor
    return bool(
        "port" in entry.entity_id.lower()
        or "poe" in entry.entity_id.lower()
        or (entry.unique_id and "port" in entry.unique_id.lower())
        or (entry.unique_id and "poe" in entry.unique_id.lower())
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up UniFi Energy Helper energy sensors from a config entry."""

    entity_registry = er.async_get(hass)

    # Store callback and config entry for dynamic entity creation
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["sensor_add_entities"] = async_add_entities
    hass.data[DOMAIN]["config_entry"] = config_entry
    hass.data[DOMAIN]["tracked_poe_entities"] = set()

    # Find all UniFi PoE power entities
    poe_entities = []

    for entity_id, entry in entity_registry.entities.items():
        if _is_poe_power_entity(entry):
            _LOGGER.debug(
                "Found UniFi PoE power entity: %s (device: %s)",
                entity_id,
                entry.device_id,
            )
            poe_entities.append((entity_id, entry))
            hass.data[DOMAIN]["tracked_poe_entities"].add(entity_id)

    # Create one energy sensor for each PoE port
    energy_sensors = []

    for poe_entity_id, poe_entry in poe_entities:
        _LOGGER.info("Creating energy sensor for PoE port: %s", poe_entity_id)

        energy_sensor = UniFiEnergyAccumulationSensor(
            hass=hass,
            device_id=poe_entry.device_id,
            poe_entity_id=poe_entity_id,
            poe_entity_entry=poe_entry,
        )
        energy_sensors.append(energy_sensor)

    if energy_sensors:
        async_add_entities(energy_sensors, True)
        _LOGGER.info("Added %d UniFi Energy Helper energy sensors", len(energy_sensors))

        # Store energy sensor info in hass.data for button platform
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        hass.data[DOMAIN]["energy_sensors"] = [
            {
                "sensor": sensor,
                "device_id": sensor._device_id,  # noqa: SLF001
                "poe_entity_id": sensor._poe_entity_id,  # noqa: SLF001
            }
            for sensor in energy_sensors
        ]

        # Trigger button platform setup now that sensors are ready
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setups(config_entry, ["button"])
        )
    else:
        _LOGGER.warning("No UniFi PoE power entities found to create energy sensors")

    # Set up entity registry listener for new PoE entities
    @callback
    def _async_entity_registry_updated(event) -> None:
        """Handle entity registry updates to detect new PoE entities."""
        if event.data["action"] != "create":
            return

        entity_id = event.data["entity_id"]

        # Skip if we're already tracking this entity
        if entity_id in hass.data[DOMAIN]["tracked_poe_entities"]:
            return

        # Get the entity entry
        registry = er.async_get(hass)
        entry = registry.async_get(entity_id)

        if not entry or not _is_poe_power_entity(entry) or not entry.device_id:
            return

        _LOGGER.info("Detected new UniFi PoE power entity: %s", entity_id)
        hass.data[DOMAIN]["tracked_poe_entities"].add(entity_id)

        # Create energy sensor for the new PoE entity
        energy_sensor = UniFiEnergyAccumulationSensor(
            hass=hass,
            device_id=entry.device_id,
            poe_entity_id=entity_id,
            poe_entity_entry=entry,
        )

        # Add the sensor
        async_add_entities([energy_sensor], True)

        # Update hass.data with new sensor info
        if "energy_sensors" not in hass.data[DOMAIN]:
            hass.data[DOMAIN]["energy_sensors"] = []
        hass.data[DOMAIN]["energy_sensors"].append(
            {
                "sensor": energy_sensor,
                "device_id": energy_sensor._device_id,  # noqa: SLF001
                "poe_entity_id": energy_sensor._poe_entity_id,  # noqa: SLF001
            }
        )

        # Create button for the new sensor
        from .button import UniFiEnergyResetButton  # noqa: PLC0415

        reset_button = UniFiEnergyResetButton(
            hass=hass,
            device_id=entry.device_id,
            energy_sensor=energy_sensor,
        )

        # Add button if button platform is available
        if "button_add_entities" in hass.data[DOMAIN]:
            hass.data[DOMAIN]["button_add_entities"]([reset_button], True)

    # Subscribe to entity registry events
    config_entry.async_on_unload(
        hass.bus.async_listen(
            er.EVENT_ENTITY_REGISTRY_UPDATED, _async_entity_registry_updated
        )
    )


class UniFiEnergyAccumulationSensor(RestoreSensor):
    """Representation of a UniFi energy accumulation sensor with state restoration."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        hass: HomeAssistant,
        device_id: str,
        poe_entity_id: str,
        poe_entity_entry: er.RegistryEntry,
    ) -> None:
        """Initialize the energy sensor."""
        self.hass = hass
        self._device_id = device_id
        self._poe_entity_id = poe_entity_id
        self._poe_entity_entry = poe_entity_entry

        # Extract port name from the PoE entity
        # Use the original name or derive from entity_id
        port_name = poe_entity_entry.original_name or poe_entity_entry.name
        if not port_name:
            # Fallback to entity_id
            port_name = poe_entity_id.split(".")[1].replace("_", " ").title()

        # Remove "Power" from the name if present, we'll add "Energy" instead
        if "Power" in port_name:
            port_name = port_name.replace("Power", "Energy")
        elif "power" in port_name.lower():
            port_name = port_name.replace("power", "Energy").replace("Power", "Energy")
        else:
            port_name = f"{port_name} Energy"

        self._attr_name = port_name

        # Create unique_id based on the PoE power sensor's unique_id
        if poe_entity_entry.unique_id:
            self._attr_unique_id = f"{poe_entity_entry.unique_id}_energy"
        else:
            # Fallback
            self._attr_unique_id = f"{poe_entity_id}_energy"

        # Energy accumulation state
        self._total_energy_kwh = 0.0
        self._last_update_time: datetime | None = None
        self._last_power_watts: float | None = None

        # For tracking state changes and reset events
        self._unsub_update = None
        self._unsub_reset = None

    @property
    def device_info(self) -> dict[str, Any] | None:
        """Return device info to link this sensor to the UniFi device."""
        # We don't create a new device; we link to the existing UniFi device
        # by not providing device_info. The device_id will be set in the registry.
        return None

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return round(self._total_energy_kwh, 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "poe_entity_id": self._poe_entity_id,
            "last_update": self._last_update_time.isoformat()
            if self._last_update_time
            else None,
            "last_power_watts": self._last_power_watts,
        }

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        # Restore previous state if available
        last_sensor_data = await self.async_get_last_sensor_data()

        if last_sensor_data and last_sensor_data.native_value is not None:
            try:
                # Type ignore needed as native_value can be various types
                self._total_energy_kwh = float(last_sensor_data.native_value)  # type: ignore[arg-type]
                _LOGGER.info(
                    "Restored energy state for %s: %.3f kWh",
                    self._poe_entity_id,
                    self._total_energy_kwh,
                )
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Could not restore energy state for %s, starting from 0",
                    self._poe_entity_id,
                )

        # Register this entity with the same device as the UniFi PoE sensors
        # Schedule this to run after entity is fully registered
        entity_registry = er.async_get(self.hass)

        @callback
        def _async_update_device():
            """Update device_id for this entity."""
            if self.entity_id:
                entity_registry.async_update_entity(
                    self.entity_id,
                    device_id=self._device_id,
                )
                _LOGGER.debug("Linked %s to device %s", self.entity_id, self._device_id)

        # Call the callback directly to update the device
        _async_update_device()

        # Track state changes of the power entity
        self._unsub_update = async_track_state_change_event(
            self.hass,
            [self._poe_entity_id],
            self._async_power_changed,
        )

        # Listen for reset events
        @callback
        def _async_handle_reset_event(event: Event) -> None:
            """Handle reset energy event."""
            if event.data.get("entity_id") == self.entity_id:
                self._reset_energy()

        self._unsub_reset = self.hass.bus.async_listen(
            f"{DOMAIN}_reset_energy",
            _async_handle_reset_event,
        )

        # Initialize with current power state
        await self._async_initialize_from_current_state()

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity removal."""
        # Calculate final energy increment before unloading
        current_time = dt_util.utcnow()
        self._calculate_energy_increment(current_time)

        # Log final state if we calculated anything
        if self._last_update_time is not None and self._last_power_watts is not None:
            _LOGGER.info(
                "Final energy state for %s before unload: Total=%.3fkWh",
                self._poe_entity_id,
                self._total_energy_kwh,
            )

        # Write the final state so it gets saved
        self.async_write_ha_state()

        # Clean up listeners
        if self._unsub_update:
            self._unsub_update()
            self._unsub_update = None
        if self._unsub_reset:
            self._unsub_reset()
            self._unsub_reset = None

    @callback
    def _reset_energy(self) -> None:
        """Reset the accumulated energy to zero."""
        _LOGGER.info(
            "Resetting energy accumulation for %s from %.3f kWh to 0",
            self._poe_entity_id,
            self._total_energy_kwh,
        )
        self._total_energy_kwh = 0.0
        self._last_update_time = dt_util.utcnow()
        # Keep the last power reading to continue tracking
        self.async_write_ha_state()

    @callback
    def _calculate_energy_increment(
        self, current_time: datetime, new_power_watts: float | None = None
    ) -> None:
        """Calculate and accumulate energy increment since last update.

        Args:
            current_time: The current timestamp
            new_power_watts: New power reading (if any) to update tracking with
        """
        # If we have a previous reading, calculate energy increment
        if self._last_update_time is not None and self._last_power_watts is not None:
            time_delta_seconds = (current_time - self._last_update_time).total_seconds()

            # Only calculate if there's been some time elapsed
            if time_delta_seconds > 0:
                # Use the previous power value for the time period that just elapsed
                # (riemann sum approach - using left endpoint)
                energy_increment_kwh = (
                    self._last_power_watts
                    * time_delta_seconds
                    * SECONDS_TO_HOURS
                    * WATTS_TO_KILOWATTS
                )

                self._total_energy_kwh += energy_increment_kwh

                if new_power_watts is not None:
                    _LOGGER.debug(
                        "Energy update for %s: Power=%.2fW→%.2fW, Delta=%.1fs, Increment=%.6fkWh, Total=%.3fkWh",
                        self._poe_entity_id,
                        self._last_power_watts,
                        new_power_watts,
                        time_delta_seconds,
                        energy_increment_kwh,
                        self._total_energy_kwh,
                    )
                else:
                    _LOGGER.debug(
                        "Energy update for %s: Power=%.2fW, Delta=%.1fs, Increment=%.6fkWh, Total=%.3fkWh",
                        self._poe_entity_id,
                        self._last_power_watts,
                        time_delta_seconds,
                        energy_increment_kwh,
                        self._total_energy_kwh,
                    )

        # Update tracking variables if new power provided
        if new_power_watts is not None:
            self._last_power_watts = new_power_watts
            self._last_update_time = current_time

    async def _async_initialize_from_current_state(self) -> None:
        """Initialize tracking from current power state."""
        state = self.hass.states.get(self._poe_entity_id)
        if state and state.state not in ("unknown", "unavailable"):
            try:
                self._last_power_watts = float(state.state)
                self._last_update_time = dt_util.utcnow()
                _LOGGER.debug(
                    "Initialized energy tracking for %s at %.2fW",
                    self._poe_entity_id,
                    self._last_power_watts,
                )
            except (ValueError, TypeError):
                _LOGGER.debug(
                    "Could not initialize from current state %s: %s",
                    self._poe_entity_id,
                    state.state,
                )
        self.async_write_ha_state()

    @callback
    def _async_power_changed(self, event) -> None:
        """Handle power entity state changes."""
        new_state = event.data.get("new_state")
        if not new_state or new_state.state in ("unknown", "unavailable"):
            return

        try:
            new_power_watts = float(new_state.state)
        except (ValueError, TypeError):
            _LOGGER.debug(
                "Invalid power reading from %s: %s",
                self._poe_entity_id,
                new_state.state,
            )
            return

        current_time = dt_util.utcnow()

        # Calculate energy increment and update tracking
        self._calculate_energy_increment(current_time, new_power_watts)
        self.async_write_ha_state()
