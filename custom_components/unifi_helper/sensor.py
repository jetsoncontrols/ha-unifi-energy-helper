"""Support for UniFi Helper energy sensors."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    UNIFI_DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    WATTS_TO_KILOWATTS,
    SECONDS_TO_HOURS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up UniFi Helper energy sensors from a config entry."""
    
    entity_registry = er.async_get(hass)
    
    # Find all UniFi PoE power entities
    poe_entities = []
    device_poe_map = {}  # Map device_id to list of PoE power entity_ids
    
    for entity_id, entry in entity_registry.entities.items():
        # Look for UniFi power sensors (PoE ports)
        if (
            entry.platform == UNIFI_DOMAIN
            and entity_id.startswith("sensor.")
            and entry.device_id
            and entry.original_device_class == SensorDeviceClass.POWER
            and entry.unit_of_measurement == UnitOfPower.WATT
        ):
            # Check if this is likely a PoE port power sensor
            # UniFi PoE sensors typically have "port" in their name or unique_id
            is_poe = (
                "port" in entity_id.lower()
                or "poe" in entity_id.lower()
                or (entry.unique_id and "port" in entry.unique_id.lower())
                or (entry.unique_id and "poe" in entry.unique_id.lower())
            )
            
            if is_poe:
                _LOGGER.debug(f"Found UniFi PoE power entity: {entity_id} (device: {entry.device_id})")
                poe_entities.append((entity_id, entry))
                
                if entry.device_id not in device_poe_map:
                    device_poe_map[entry.device_id] = []
                device_poe_map[entry.device_id].append(entity_id)
    
    # Create energy sensors for each device that has PoE ports
    device_registry = dr.async_get(hass)
    energy_sensors = []
    
    for device_id, poe_entity_ids in device_poe_map.items():
        _LOGGER.info(
            f"Creating energy sensor for device {device_id} with {len(poe_entity_ids)} PoE ports"
        )
        
        # Get device name from the device registry
        device_name = None
        device_entry = device_registry.async_get(device_id)
        if device_entry:
            # Use the device's name from the registry
            device_name = device_entry.name_by_user or device_entry.name
        
        if not device_name:
            # Fallback to extracting from entity name (shouldn't happen normally)
            device_name = f"UniFi Device {device_id[:8]}"
        
        energy_sensor = UniFiEnergyAccumulationSensor(
            hass=hass,
            device_id=device_id,
            device_name=device_name,
            poe_entity_ids=poe_entity_ids,
        )
        energy_sensors.append(energy_sensor)
    
    if energy_sensors:
        async_add_entities(energy_sensors, True)
        _LOGGER.info(f"Added {len(energy_sensors)} UniFi Helper energy sensors")
    else:
        _LOGGER.warning("No UniFi PoE power entities found to create energy sensors")


class UniFiEnergyAccumulationSensor(RestoreSensor):
    """Representation of a UniFi energy accumulation sensor with state restoration."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        device_id: str,
        device_name: str,
        poe_entity_ids: list[str],
    ) -> None:
        """Initialize the energy sensor."""
        self.hass = hass
        self._device_id = device_id
        self._device_name = device_name
        self._poe_entity_ids = poe_entity_ids
        self._attr_name = "PoE Energy"
        self._attr_unique_id = f"{device_id}_poe_energy"
        
        # Energy accumulation state
        self._total_energy_kwh = 0.0
        self._last_update = None
        self._update_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
        
        # For tracking
        self._unsub_update = None

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
            "poe_entity_ids": self._poe_entity_ids,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        # Restore previous state if available
        last_state = await self.async_get_last_state()
        last_sensor_data = await self.async_get_last_sensor_data()
        
        if last_sensor_data and last_sensor_data.native_value is not None:
            try:
                self._total_energy_kwh = float(last_sensor_data.native_value)
                _LOGGER.info(
                    f"Restored energy state for {self._device_name}: {self._total_energy_kwh:.3f} kWh"
                )
            except (ValueError, TypeError):
                _LOGGER.warning(
                    f"Could not restore energy state for {self._device_name}, starting from 0"
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
                _LOGGER.debug(f"Linked {self.entity_id} to device {self._device_id}")
        
        # Schedule the device update to run after entity is registered
        self.hass.async_create_task(_async_update_device())
        
        # Start periodic updates
        self._unsub_update = async_track_time_interval(
            self.hass,
            self._async_update,
            self._update_interval,
        )
        
        # Initial update
        await self._async_update(None)

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity removal."""
        if self._unsub_update:
            self._unsub_update()
            self._unsub_update = None

    @callback
    async def _async_update(self, now: datetime | None = None) -> None:
        """Update the energy accumulation."""
        current_time = dt_util.utcnow()
        
        # Calculate time delta
        if self._last_update is None:
            # First update - don't accumulate energy yet
            self._last_update = current_time
            self.async_write_ha_state()
            return
        
        time_delta_seconds = (current_time - self._last_update).total_seconds()
        
        # Get current power from all PoE ports
        total_power_watts = 0.0
        valid_readings = 0
        
        for entity_id in self._poe_entity_ids:
            state = self.hass.states.get(entity_id)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    power = float(state.state)
                    total_power_watts += power
                    valid_readings += 1
                except (ValueError, TypeError):
                    _LOGGER.debug(f"Invalid power reading from {entity_id}: {state.state}")
        
        # Only accumulate if we have valid readings
        if valid_readings > 0:
            # Calculate energy: Power (W) * Time (s) / 3600 / 1000 = Energy (kWh)
            energy_increment_kwh = (
                total_power_watts * time_delta_seconds * SECONDS_TO_HOURS * WATTS_TO_KILOWATTS
            )
            
            self._total_energy_kwh += energy_increment_kwh
            
            _LOGGER.debug(
                f"Energy update for {self._device_name}: "
                f"Power={total_power_watts}W, Delta={time_delta_seconds}s, "
                f"Increment={energy_increment_kwh:.6f}kWh, Total={self._total_energy_kwh:.3f}kWh"
            )
        
        self._last_update = current_time
        self.async_write_ha_state()
