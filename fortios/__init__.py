"""FortiOS Device Tracker integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_SCAN_INTERVAL, CONF_VDOM, DOMAIN
from .firewall import FortiOSAPI, FortiOSFirewall

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.DEVICE_TRACKER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FortiOS from a config entry."""
    _LOGGER.debug("Setting up FortiOS entry: %s", entry.entry_id)

    api = FortiOSAPI(entry.data[CONF_HOST], entry.data[CONF_PORT],
                     entry.data[CONF_TOKEN], entry.data[CONF_VDOM],
                     entry.data[CONF_VERIFY_SSL])
    # Set up firewall
    fgt = FortiOSFirewall(hass, entry, api)

    # Do initial data update
    # await hass.async_add_executor_job(fgt.update_all)
    await fgt.update_all()
    entry.async_on_unload(
        async_track_time_interval(
            hass, fgt.update_all, timedelta(seconds=float(entry.data[CONF_SCAN_INTERVAL])))
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.unique_id] = fgt

    # Forward the entry setups for all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading FortiOS entry: %s", entry.entry_id)

    unload_response = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_response:
        hass.data[DOMAIN].pop(entry.unique_id)

    return unload_response
