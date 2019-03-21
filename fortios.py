"""
Support for FortiOS equipment like Fortigate.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.fortios/
"""

import logging
import voluptuous as vol
from datetime import timedelta
from fortiosapi import FortiOSAPI

import homeassistant.helpers.config_validation as cv
from homeassistant.components.device_tracker import (
    DOMAIN, PLATFORM_SCHEMA, DeviceScanner)
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.const import CONF_VERIFY_SSL
from homeassistant.components.device_tracker import CONF_CONSIDER_HOME

REQUIREMENTS = ['fortiosapi==0.10.4']

_LOGGER = logging.getLogger(__name__)
DEFAULT_VERIFY_SSL = True

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_TOKEN): cv.string,
    vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
    vol.Optional(CONF_CONSIDER_HOME, default=180): cv.timedelta
})

def get_scanner(hass, config):
    """Validate the configuration and return a FortiOSDeviceScanner."""
    _LOGGER.debug('fortios, get_scanner')

    scanner = FortiOSDeviceScanner(config[DOMAIN])

    return scanner if scanner.success_init else None


class FortiOSDeviceScanner(DeviceScanner):
    """This class queries a FortiOS unit for connected devices."""

    def __init__(self, config):
        """Initialize the scanner."""
        self.host = config.get(CONF_HOST)
        self.verify_ssl = config.get(CONF_VERIFY_SSL)
        self.token = config.get(CONF_TOKEN)
        self.consider_home = config.get(CONF_CONSIDER_HOME)
        self.last_results = {}

        self.fgt = FortiOSAPI()

        try:
            fgt.tokenlogin(self, self.host, self.token)
        except Exception as e:
            self.fail("Exception : %s" + str(e))

        self.success_init = self._update_info()
        _LOGGER.info('FortiOSDeviceScanner initialized')

    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        self._update_info()

        return self.last_results

    def get_device_name(self, device):
        """Return the name of the given device or None if we don't know."""
        import json

        _LOGGER.debug("get_device_name device=%s", device)

        device = device.lower()

        data = self.last_results_json

        if data == 0:
            _LOGGER.error('get_device_name no json results')
            return None

        for p in data['results']:
            if p['mac'] == device:
                try:
                    name = p['host']['name']
                    _LOGGER.debug("get_device_name name=%s", name)
                    return name
                except:
                    return None

        return None


    def _update_info(self):
        """
        Ensure the information from the FortiOS is up to date.
        Retrieve data from FortiOS and return parsed result.
        """

        dict_result = self.fgt.monitor('user/device/select','')

        if dict_result:
            self.last_results = []
            self.last_results = \
                self._parse_fortios_response(dict_result)
            return True

        return False

    def _parse_fortios_response(self, data):
        """Parse the FortiOS data format."""

        maclines = []

        for p in data['results']:
            if p['last_seen'] < self.consider_home.total_seconds():
                maclines.append(p['mac'].upper())

        return maclines
