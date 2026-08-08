"""Config and options flow for the YouLess (custom) integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import YoulessConfigEntry, build_device

_INTERVAL_SELECTOR = vol.All(
    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
)


async def _test_connection(hass: HomeAssistant, data: dict[str, Any]) -> str | None:
    """Attempt a connection and return the device MAC (unique id)."""
    device = build_device(data)
    await hass.async_add_executor_job(device.initialize)
    return getattr(device, "mac_address", None)


class YoulessConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the form shown when the user adds the integration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                mac = await _test_connection(self.hass, user_input)
            except Exception:  # noqa: BLE001 - library raises bare requests errors
                errors["base"] = "cannot_connect"
            else:
                if mac:
                    await self.async_set_unique_id(mac)
                    self._abort_if_unique_id_configured()

                interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or DEFAULT_NAME,
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_NAME: user_input.get(CONF_NAME) or DEFAULT_NAME,
                        CONF_USERNAME: user_input.get(CONF_USERNAME, ""),
                        CONF_PASSWORD: user_input.get(CONF_PASSWORD, ""),
                    },
                    options={CONF_SCAN_INTERVAL: interval},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Optional(CONF_USERNAME, default=""): str,
                vol.Optional(CONF_PASSWORD, default=""): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): _INTERVAL_SELECTOR,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: YoulessConfigEntry,
    ) -> YoulessOptionsFlow:
        """Return the options flow handler."""
        return YoulessOptionsFlow()


class YoulessOptionsFlow(OptionsFlow):
    """Allow changing the poll interval after setup.

    In current Home Assistant, ``self.config_entry`` is provided by the
    framework automatically - do not set it in ``__init__``.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the poll interval option."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL, default=current
                ): _INTERVAL_SELECTOR,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
