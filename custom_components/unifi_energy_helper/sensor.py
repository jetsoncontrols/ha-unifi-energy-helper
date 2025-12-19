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


def _is_unifi_power_entity(entry: er.RegistryEntry) -> bool:
    """Check if an entity registry entry is a UniFi PoE port or PDU outlet power sensor."""
    if not (
        entry.platform == UNIFI_DOMAIN
        and entry.entity_id.startswith("sensor.")
        and entry.device_id
        and entry.original_device_class == SensorDeviceClass.POWER
        and entry.unit_of_measurement == UnitOfPower.WATT
        and entry.disabled_by is None
    ):
        return False

    # Check if this is a PoE port power sensor or PDU outlet power sensor
    entity_lower = entry.entity_id.lower()
    unique_lower = entry.unique_id.lower() if entry.unique_id else ""
    
    return bool(
        "port" in entity_lower
        or "poe" in entity_lower
        or "outlet" in entity_lower
        or "pdu" in entity_lower
        or "port" in unique_lower
        or "poe" in unique_lower
        or "outlet" in unique_lower
        or "pdu" in unique_lower
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

    # Find all UniFi PoE port and PDU outlet power entities
    power_entities = []

    for entity_id, entry in entity_registry.entities.items():
        if _is_unifi_power_entity(entry):
            _LOGGER.debug(
                "Found UniFi power entity: %s (device: %s)",
                entity_id,
                entry.device_id,
            )
            power_entities.append((entity_id, entry))
            hass.data[DOMAIN]["tracked_poe_entities"].add(entity_id)

    # Create one energy sensor for each PoE port / PDU outlet
    energy_sensors = []

    for power_entity_id, power_entry in power_entities:
        _LOGGER.info("Creating energy sensor for power entity: %s", power_entity_id)

        energy_sensor = UniFiEnergyAccumulationSensor(
            hass=hass,
            device_id=power_entry.device_id,
            poe_entity_id=power_entity_id,
            poe_entity_entry=power_entry,
            config_entry_id=config_entry.entry_id,
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
        _LOGGER.warning("No UniFi PoE or PDU power entities found to create energy sensors")

    # Set up entity registry listener for new PoE/PDU entities
    @callback
    def _async_entity_registry_updated(event) -> None:
        """Handle entity registry updates to detect new or enabled PoE/PDU power entities."""
        action = event.data["action"]

        # Handle both new entities and entities being enabled
        if action == "create":
            entity_id = event.data["entity_id"]
        elif action == "update":
            entity_id = event.data["entity_id"]
            changes = event.data.get("changes", {})

            # Only process if the entity was enabled (disabled_by changed from something to None)
            if "disabled_by" not in changes:
                return

            # Check if entity was just enabled
            old_disabled = changes.get("disabled_by")
            registry = er.async_get(hass)
            entry = registry.async_get(entity_id)

            if not entry or entry.disabled_by is not None or old_disabled is None:
                return

            _LOGGER.debug("Detected power entity being enabled: %s", entity_id)
        else:
            return

        # Skip if we're already tracking this entity
        if entity_id in hass.data[DOMAIN]["tracked_poe_entities"]:
            return

        # Get the entity entry
        registry = er.async_get(hass)
        entry = registry.async_get(entity_id)

        if not entry or not _is_unifi_power_entity(entry) or not entry.device_id:
            return

        _LOGGER.info("Detected new/enabled UniFi power entity: %s", entity_id)
        hass.data[DOMAIN]["tracked_poe_entities"].add(entity_id)

        # Create energy sensor for the new PoE entity
        config_entry = hass.data[DOMAIN].get("config_entry")
        energy_sensor = UniFiEnergyAccumulationSensor(
            hass=hass,
            device_id=entry.device_id,
            poe_entity_id=entity_id,
            poe_entity_entry=entry,
            config_entry_id=config_entry.entry_id if config_entry else None,
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
            config_entry_id=energy_sensor._attr_config_entry_id
            if hasattr(energy_sensor, "_attr_config_entry_id")
            else None,  # noqa: SLF001
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
        config_entry_id: str | None = None,
    ) -> None:
        """Initialize the energy sensor."""
        self.hass = hass
        self._device_id = device_id
        self._poe_entity_id = poe_entity_id
        self._poe_entity_entry = poe_entity_entry

        # Link to config entry
        if config_entry_id:
            self._attr_config_entry_id = config_entry_id

        # Extract name from the power entity (PoE port or PDU outlet)
        # Use the original name or derive from entity_id
        power_name = poe_entity_entry.original_name or poe_entity_entry.name
        if not power_name:
            # Fallback to entity_id
            power_name = poe_entity_id.split(".")[1].replace("_", " ").title()

        # Remove various power-related suffixes and replace with "Energy"
        # Handle variations like "Port 1 PoE Power", "Outlet 5 Outlet Power", "Port Power", etc.
        if "Power" in power_name:
            # Replace "Power" with "Energy", handling duplicates like "Outlet 5 Outlet Power"
            energy_name = power_name.replace(" Power", " Energy")
            # Clean up duplicates like "Outlet 5 Outlet Energy" -> "Outlet 5 Energy"
            if "Outlet" in energy_name and energy_name.count("Outlet") > 1:
                # Remove the redundant "Outlet" before "Energy"
                energy_name = energy_name.replace(" Outlet Energy", " Energy")
        elif "power" in power_name.lower():
            energy_name = power_name.replace("power", "Energy").replace("Power", "Energy")
        else:
            energy_name = f"{power_name} Energy"

        self._attr_name = energy_name

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
        self._unsub_registry = None

    def _update_name_from_poe_entity(self, poe_entry: er.RegistryEntry) -> None:
        """Update sensor name based on power entity name."""
        power_name = poe_entry.original_name or poe_entry.name
        if not power_name:
            # Fallback to entity_id
            power_name = self._poe_entity_id.split(".")[1].replace("_", " ").title()

        # Remove various power-related suffixes and replace with "Energy"
        # Handle variations like "Port 1 PoE Power", "Outlet 5 Outlet Power", "Port Power", etc.
        if "Power" in power_name:
            # Replace "Power" with "Energy", handling duplicates like "Outlet 5 Outlet Power"
            energy_name = power_name.replace(" Power", " Energy")
            # Clean up duplicates like "Outlet 5 Outlet Energy" -> "Outlet 5 Energy"
            if "Outlet" in energy_name and energy_name.count("Outlet") > 1:
                # Remove the redundant "Outlet" before "Energy"
                energy_name = energy_name.replace(" Outlet Energy", " Energy")
        elif "power" in power_name.lower():
            energy_name = power_name.replace("power", "Energy").replace("Power", "Energy")
        else:
            energy_name = f"{power_name} Energy"

        if self._attr_name != energy_name:
            _LOGGER.debug(
                "Updating energy sensor name from '%s' to '%s'",
                self._attr_name,
                energy_name,
            )
            self._attr_name = energy_name
            self.async_write_ha_state()

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

    async def async_internal_added_to_hass(self) -> None:
        """Call when the entity is added to hass (including when enabled)."""
        await super().async_internal_added_to_hass()

        # Set up state tracking if not already set up and entity is enabled
        if self._unsub_update is None and self.enabled:
            self._unsub_update = async_track_state_change_event(
                self.hass,
                [self._poe_entity_id],
                self._async_power_changed,
            )
            _LOGGER.debug("Started tracking state for %s", self._poe_entity_id)

    async def async_internal_will_remove_from_hass(self) -> None:
        """Call when the entity is about to be removed from hass (including when disabled)."""
        await super().async_internal_will_remove_from_hass()

        # Clean up listeners when disabled
        self._cleanup_listeners()
        _LOGGER.debug("Stopped tracking state for %s", self._poe_entity_id)

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

        # Listen for PoE entity name changes
        @callback
        def _async_handle_poe_registry_update(event: Event) -> None:
            """Handle PoE entity registry updates to sync names."""
            if event.data.get("action") != "update":
                return
            
            updated_entity_id = event.data.get("entity_id")
            if updated_entity_id != self._poe_entity_id:
                return
            
            changes = event.data.get("changes", {})
            # Check if name or original_name changed
            if "name" in changes or "original_name" in changes:
                entity_registry = er.async_get(self.hass)
                poe_entry = entity_registry.async_get(self._poe_entity_id)
                if poe_entry:
                    self._update_name_from_poe_entity(poe_entry)

        self._unsub_registry = self.hass.bus.async_listen(
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            _async_handle_poe_registry_update,
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
        self._cleanup_listeners()

    def _cleanup_listeners(self) -> None:
        """Clean up state change listeners."""
        if self._unsub_update:
            self._unsub_update()
            self._unsub_update = None
        if self._unsub_reset:
            self._unsub_reset()
            self._unsub_reset = None
        if self._unsub_registry:
            self._unsub_registry()
            self._unsub_registry = None

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
