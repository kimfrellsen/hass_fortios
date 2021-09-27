import logging
from datetime import timedelta
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.device_tracker import (
    DOMAIN, PLATFORM_SCHEMA, DeviceScanner)
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.const import CONF_VERIFY_SSL
#import homeassistant.util.dt as dt_util

REQUIREMENTS = ['fortiosapi==1.0.5']

_LOGGER = logging.getLogger(__name__)
DEFAULT_VERIFY_SSL = True

#NOTIFICATION_ID = 'fortios_notification'
#NOTIFICATION_TITLE = 'FortiOS Device Tracker Setup'


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_TOKEN): cv.string,
    vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean
})

def get_scanner(hass, config):
    """Validate the configuration and return a FortiOSDeviceScanner."""
    from fortiosapi import FortiOSAPI

    host = str(config.get(CONF_HOST))
    verify_ssl = config.get(CONF_VERIFY_SSL)
    token = str(config.get(CONF_TOKEN))

    _LOGGER.debug('fortios, get_scanner')

    fgt = FortiOSAPI()

    try:
        fgt.tokenlogin(host, token)
    except Exception as e:
        _LOGGER.error("Unable login to fgt Exception : %s" + str(e))


    try:
        scanner = FortiOSDeviceScanner(fgt)
    except Exception as e:
        _LOGGER.error("FortiOS get_scanner Initialize failed %s" + str(e))
        return False

    return scanner


class FortiOSDeviceScanner(DeviceScanner):
    """This class queries a FortiOS unit for connected devices."""

    def __init__(self, fgt) -> None:
        """Initialize the scanner."""
        _LOGGER.debug('__init__')
        self.last_results = {}
        self._update()
        self.fgt = fgt

    def _update(self):
        """Get the clients from the device."""
        """
        Ensure the information from the FortiOS is up to date.
        Retrieve data from FortiOS and return parsed result.
        """
        _LOGGER.debug('_update(self)')

        dict_result = self.fgt.monitor('user/device/select','')
        self.last_results_json = dict_result

        self.last_results = []

        if dict_result:
            for p in dict_result['results']:
                self.last_results.append(p['mac'].upper())


    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        _LOGGER.debug('scan_devices(self)')
        self._update()
        return self.last_results

    def get_device_name(self, device):
        """Return the name of the given device or None if we don't know."""
        _LOGGER.debug('get_device_name(self, device)')

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
