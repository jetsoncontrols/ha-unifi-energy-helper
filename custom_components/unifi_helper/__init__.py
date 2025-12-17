"""The UniFi Helper integration."""
from __future__ import annotations

import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the UniFi Helper component.
    
    This integration uses async_setup instead of config entries because it:
    1. Requires no user configuration (auto-discovery only)
    2. Has no settings to configure
    3. Simply wraps existing UniFi integration entities
    
    For a simple helper integration, this approach is more straightforward
    than implementing a full config entry flow.
    """
    hass.data.setdefault(DOMAIN, {})
    
    # Set up sensor platform
    await async_load_platform(hass, Platform.SENSOR, DOMAIN, {}, config)
    
    return True
