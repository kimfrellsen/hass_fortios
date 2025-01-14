"""Config flow for the FortiOS device tracker platform."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from awesomeversion import AwesomeVersion
from requests.exceptions import RequestException
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_VERIFY_SSL,
)

from .const import (
    CONF_VDOM,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VDOM,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    MINIMUM_SUPPORTED_VERSION,
)
from .firewall import FortiOSAPI

_LOGGER = logging.getLogger(__name__)


class UnsupportedFortiOSVersion(Exception):
    """Exception to indicate unsupported FortiOS version."""


class FortiOSFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FortiOS."""

    VERSION = 1
    MINOR_VERSION = 0

    def __init__(self) -> None:
        """Initialize config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                        vol.Required(CONF_TOKEN): str,
                        vol.Required(CONF_VDOM, default=DEFAULT_VDOM): str,
                        vol.Required(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
                        vol.Required(
                            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                        ): int,
                    }
                ),
                errors={},
            )

        self._data = user_input

        # Check if already configured
        await self.async_set_unique_id(self._data[CONF_HOST])
        self._abort_if_unique_id_configured()

        return await self.async_step_link()

    async def async_step_link(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Attempt to link with the FortiGate Firewall."""

        errors = {}

        fgt = FortiOSAPI(
            self._data[CONF_HOST],
            self._data[CONF_PORT],
            self._data[CONF_TOKEN],
            self._data[CONF_VDOM],
            self._data[CONF_VERIFY_SSL],
        )
        try:
            # Check if the FortiOS device is reachable
            response = await fgt.get("monitor/system/status")

            if response is None:
                raise Exception("No response from FortiOS device")

            version = response["version"]

            if AwesomeVersion(version) < AwesomeVersion(MINIMUM_SUPPORTED_VERSION):
                _LOGGER.error(
                    "Unsupported FortiOS version: %s. It must be at least %s",
                    version,
                    MINIMUM_SUPPORTED_VERSION,
                )
                # raise Exception("Unsupported FortiOS version: %s", version)
                raise UnsupportedFortiOSVersion(
                    f"Unsupported FortiOS version: {version}. It must be at least {MINIMUM_SUPPORTED_VERSION}"
                )

            # Assign a unique ID to the flow and abort the flow
            # if another flow with the same unique ID is in progress
            await self.async_set_unique_id(response["serial"])

            # Abort the flow if a config entry with the same unique ID exists
            self._abort_if_unique_id_configured()

            # Assign a unique ID to the flow and abort the flow
            # if another flow with the same unique ID is in progress

            return self.async_create_entry(
                title=self._data[CONF_HOST],
                data=self._data,
            )

        except aiohttp.ClientResponseError as error:
            if error.status == 401:
                _LOGGER.error("Unauthorized: %s", error)
                errors["base"] = "Unauthorized. Maybe the token is invalid."
            else:
                _LOGGER.error("ClientResponseError: %s", error)
                errors["base"] = f"Error: {error}"
        except RequestException as error:
            _LOGGER.error(error)
            errors["base"] = error
        except Exception as error:
            _LOGGER.error("Unexpected exception: %s", error)
            errors["base"] = "unknown_error"

        return self.async_show_form(step_id="link", errors=errors)
