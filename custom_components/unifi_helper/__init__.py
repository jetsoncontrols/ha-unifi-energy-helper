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
    """Set up the UniFi Helper component."""
    hass.data.setdefault(DOMAIN, {})
    
    # Set up sensor platform
    await async_load_platform(hass, Platform.SENSOR, DOMAIN, {}, config)
    
    return True
