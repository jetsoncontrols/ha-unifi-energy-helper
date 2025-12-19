"""Support for UniFi Energy Helper reset buttons."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up UniFi Energy Helper reset buttons from a config entry."""

    # Store callback for dynamic button creation
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["button_add_entities"] = async_add_entities

    # Get energy sensor info from hass.data
    if "energy_sensors" not in hass.data[DOMAIN]:
        _LOGGER.debug("No energy sensors found in hass.data yet")
        return

    energy_sensors_data = hass.data[DOMAIN]["energy_sensors"]
    reset_buttons = []

    for sensor_data in energy_sensors_data:
        sensor = sensor_data["sensor"]
        device_id = sensor_data["device_id"]
        poe_entity_id = sensor_data["poe_entity_id"]

        _LOGGER.debug(
            "Creating reset button for energy sensor with PoE entity: %s",
            poe_entity_id,
        )

        reset_button = UniFiEnergyResetButton(
            hass=hass,
            device_id=device_id,
            energy_sensor=sensor,
        )
        reset_buttons.append(reset_button)

    if reset_buttons:
        async_add_entities(reset_buttons, True)
        _LOGGER.info("Added %d UniFi Energy Helper reset buttons", len(reset_buttons))
    else:
        _LOGGER.debug("No UniFi Energy Helper energy sensors found to create reset buttons")


class UniFiEnergyResetButton(ButtonEntity):
    """Representation of a button to reset UniFi energy accumulation."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        hass: HomeAssistant,
        device_id: str,
        energy_sensor: Any,
    ) -> None:
        """Initialize the reset button."""
        self.hass = hass
        self._device_id = device_id
        self._energy_sensor = energy_sensor

        # Extract name from the energy sensor
        energy_name = energy_sensor._attr_name or "Energy"  # noqa: SLF001

        # Create button name (e.g., "Port 1 Energy" -> "Port 1 Reset Energy")
        # Put port name first so it groups alphabetically with the power sensor
        if energy_name.endswith(" Energy"):
            # Replace " Energy" with " Reset Energy"
            self._attr_name = energy_name.replace(" Energy", " Reset Energy")
        else:
            # Fallback - just append Reset
            self._attr_name = f"{energy_name} Reset"

        # Create unique_id based on the energy sensor's unique_id
        if hasattr(energy_sensor, "_attr_unique_id") and energy_sensor._attr_unique_id:  # noqa: SLF001
            self._attr_unique_id = f"{energy_sensor._attr_unique_id}_reset"  # noqa: SLF001
        else:
            # Fallback
            self._attr_unique_id = f"{energy_sensor._poe_entity_id}_energy_reset"  # noqa: SLF001

    @property
    def device_info(self) -> dict[str, Any] | None:
        """Return device info to link this button to the UniFi device."""
        # We don't create a new device; we link to the existing UniFi device
        # by not providing device_info. The device_id will be set in the registry.
        return None

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        # Register this entity with the same device as the energy sensor
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

    async def async_press(self) -> None:
        """Handle the button press to reset energy accumulation."""
        # Call reset method directly on the sensor
        if hasattr(self._energy_sensor, "_reset_energy"):
            _LOGGER.info(
                "Resetting energy accumulation for %s",
                self._energy_sensor._poe_entity_id,  # noqa: SLF001
            )
            self._energy_sensor._reset_energy()  # noqa: SLF001
        else:
            _LOGGER.error(
                "Energy sensor does not have _reset_energy method: %s",
                self._energy_sensor._poe_entity_id,  # noqa: SLF001
            )
