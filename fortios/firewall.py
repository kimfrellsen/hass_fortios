"""Represent the FortiGate firewall and its devices and sensors."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import CONF_VDOM, DOMAIN, FORTIOS_RESULTS_MASTER_MAC, REST_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class FortiOSAPI:
    """FortiOS API wrapper."""

    def __init__(self, host: str, port: int, token: str, vdom: str, verify_ssl: bool) -> None:
        """Initialize the FortiOS API wrapper."""
        self._host = host
        self._port = port
        self._token = token
        self._vdom = vdom
        self._verify_ssl = verify_ssl

    async def get(self, path: str) -> dict[str, Any]:
        """Perform a GET request."""
        url = f"https://{self._host}:{self._port}/api/v2/{path}"
        headers = {"Authorization": f"Bearer {self._token}"}
        parameters = {"vdom": self._vdom}

        async with ClientSession(
            timeout=ClientTimeout(total=REST_TIMEOUT),
            connector=TCPConnector(ssl=self._verify_ssl),
        ) as session:
            try:
                async with session.get(url, headers=headers, params=parameters) as response:
                    # async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as ex:
                _LOGGER.error(
                    "Error performing GET request to %s: %s", url, ex)
                raise


class FortiOSFirewall:
    """Representation of a FortiOS firewall."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: FortiOSAPI,
    ) -> None:
        """Initialize a FortiGate firewall."""
        self.hass = hass
        self._host = entry.data[CONF_HOST]
        self._port = entry.data[CONF_PORT]
        self._token = entry.data[CONF_TOKEN]
        self._vdom = entry.data[CONF_VDOM]
        self._verify_ssl = entry.data[CONF_VERIFY_SSL]
        self._api = api

        self.supports_hosts = True
        self.devices: dict[str, dict[str, Any]] = {}

    async def update_all(self, now: datetime | None = None) -> None:
        """Update all FortiGate platforms."""
        _LOGGER.debug("update_all")
        await self.update_device_trackers()

    async def update_device_trackers(self) -> None:
        """Update FortiGate scanned entities."""
        _LOGGER.debug("update_device_trackers")

        new_device = False
        fortios_devices: list[dict[str, Any]] = []

        fortios_devices = await self._api.get("monitor/user/device/query")
        for device in fortios_devices["results"]:
            mac = device[FORTIOS_RESULTS_MASTER_MAC]

            if mac not in self.devices:
                new_device = True

            self.devices[mac] = device

        async_dispatcher_send(self.hass, self.signal_device_update)

        if new_device:
            async_dispatcher_send(self.hass, self.signal_device_new)

    @property
    def signal_device_update(self) -> str:
        """Event specific per FortiOS entry to signal updates in devices."""
        return f"{DOMAIN}-{self._host}-device-update"

    @property
    def signal_device_new(self) -> str:
        """Event specific per FortiOS entry to signal new device."""
        return f"{DOMAIN}-{self._host}-device-new"
