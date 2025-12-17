"""Support for UniFi Helper energy sensors."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.sensor import (
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
from homeassistant.helpers import entity_registry as er
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
    """Set up UniFi Helper energy sensors."""
    
    # This runs without config flow, so we need to discover entities automatically
    await async_setup_platform(hass, {}, async_add_entities)


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info: dict | None = None,
) -> None:
    """Set up the UniFi Helper energy sensors."""
    
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
            if "port" in entity_id.lower() or "poe" in entity_id.lower():
                _LOGGER.debug(f"Found UniFi PoE power entity: {entity_id} (device: {entry.device_id})")
                poe_entities.append((entity_id, entry))
                
                if entry.device_id not in device_poe_map:
                    device_poe_map[entry.device_id] = []
                device_poe_map[entry.device_id].append(entity_id)
    
    # Create energy sensors for each device that has PoE ports
    energy_sensors = []
    for device_id, poe_entity_ids in device_poe_map.items():
        _LOGGER.info(
            f"Creating energy sensor for device {device_id} with {len(poe_entity_ids)} PoE ports"
        )
        
        # Get device name from one of the entities
        device_name = None
        for entity_id in poe_entity_ids:
            entity_entry = entity_registry.entities.get(entity_id)
            if entity_entry and entity_entry.device_id:
                device_name = entity_entry.name or entity_entry.original_name
                if device_name:
                    # Extract device name from port name (e.g., "Switch Port 1" -> "Switch")
                    device_name = device_name.split(" Port ")[0] if " Port " in device_name else device_name
                    device_name = device_name.split(" POE ")[0] if " POE " in device_name.upper() else device_name
                    break
        
        if not device_name:
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


class UniFiEnergyAccumulationSensor(SensorEntity):
    """Representation of a UniFi energy accumulation sensor."""

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
        
        # Register this entity with the same device as the UniFi PoE sensors
        entity_registry = er.async_get(self.hass)
        if self.entity_id:
            entity_registry.async_update_entity(
                self.entity_id,
                device_id=self._device_id,
            )
        
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
