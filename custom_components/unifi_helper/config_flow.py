"""Config flow for UniFi Helper integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, UNIFI_DOMAIN

_LOGGER = logging.getLogger(__name__)


async def _async_has_unifi_poe_devices(hass: HomeAssistant) -> bool:
    """Check if there are any UniFi PoE devices available."""
    entity_registry = er.async_get(hass)
    
    for entity_id, entry in entity_registry.entities.items():
        if (
            entry.platform == UNIFI_DOMAIN
            and entity_id.startswith("sensor.")
            and entry.device_id
            and ("poe" in entity_id.lower() or "port" in entity_id.lower())
        ):
            return True
    return False


class UniFiHelperConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UniFi Helper."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        # Check if already configured
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        # Check if UniFi integration is available with PoE devices
        if not await _async_has_unifi_poe_devices(self.hass):
            return self.async_abort(reason="no_unifi_poe_devices")

        if user_input is not None:
            return self.async_create_entry(title="UniFi Helper", data={})

        return self.async_show_form(step_id="user")

    async def async_step_import(self, import_data: dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        # Check if already configured
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(title="UniFi Helper", data={})
