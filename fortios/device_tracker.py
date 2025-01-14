"""FortiOS device tracker platform."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.device_tracker import ScannerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEFAULT_DEVICE_NAME, DEVICE_ICONS, DOMAIN
from .firewall import FortiOSFirewall

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up FortiOS device tracker from a config entry."""
    firewall: FortiOSFirewall = hass.data[DOMAIN][entry.unique_id]
    tracked: set[str] = set()

    @callback
    def update_firewall() -> None:
        """Update the values of the router."""
        add_entities(firewall, async_add_entities, tracked)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, firewall.signal_device_new, update_firewall)
    )

    update_firewall()


@callback
def add_entities(
    firewall: FortiOSFirewall,
    async_add_entities: AddEntitiesCallback,
    tracked: set[str],
) -> None:
    """Add new tracker entities from the router."""
    new_tracked = []

    for mac, device in firewall.devices.items():
        if mac in tracked:
            continue

        new_tracked.append(FortiOSDeviceScanner(firewall, device))
        tracked.add(mac)

    async_add_entities(new_tracked, True)


class FortiOSDeviceScanner(ScannerEntity):
    """Representation of a FortiOS connected device."""

    _is_connected: bool = False
    entity_registry_enabled_default = True

    def __init__(self, firewall: FortiOSFirewall, device: dict[str, Any]) -> None:
        """Initialize a FortiOS device."""
        self._firewall = firewall
        self._attr_name = device.get("hostname", DEFAULT_DEVICE_NAME).strip()
        self._attr_hostname = device.get(
            "hostname", device.get("master_mac", DEFAULT_DEVICE_NAME).strip()
        )
        self._attr_ip_address = device.get("ipv4_address", "")
        # self._mac = device.get("master_mac", "")
        self._attr_mac_address = device.get("master_mac", "")
        self._attr_icon = icon_for_fortios_device(device)
        self._is_connected = False
        self._attr_extra_state_attributes: dict[str, Any] = {}

    @callback
    def async_update_state(self) -> None:
        """Update the FortiOS device."""
        device = self._firewall.devices[self._attr_mac_address]
        self._is_connected = device.get("is_online", False)
        self._attr_extra_state_attributes = {
            "last_seen": datetime.fromtimestamp(device.get("last_seen", "")),
            "OS_name": device.get("os_name", ""),
            "IPv6 Address": device.get("ipv6_address", ""),
            "Hardware vendor": device.get("hardware_vendor", ""),
            "Hardware type": device.get("hardware_type", ""),
            "Hardware version": device.get("hardware_version", ""),
            "Hardware family": device.get("hardware_family", ""),
        }

    @property
    def mac_address(self) -> str:
        """Return a unique ID."""
        return self._attr_mac_address

    @property
    def name(self) -> str:
        """Return the name."""
        return self._attr_name

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected to the network."""
        return self._is_connected

    @callback
    def async_on_demand_update(self) -> None:
        """Update state."""
        self.async_update_state()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register state update callback."""
        self.async_update_state()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self._router.signal_device_update,
                self.async_on_demand_update,
            )
        )


def icon_for_fortios_device(device: dict[str, Any]) -> str:
    """Return a device icon from its type."""
    return DEVICE_ICONS.get(
        str(device.get("hardware_family", "")).lower(), "mdi:help-network"
    )
