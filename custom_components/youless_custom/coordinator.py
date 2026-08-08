"""DataUpdateCoordinator for the YouLess (custom) integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Mapping

from youless_api import YoulessAPI

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
)

# Typed config entry so the coordinator is available via entry.runtime_data
type YoulessConfigEntry = ConfigEntry[YoulessCoordinator]


def build_device(data: Mapping[str, Any]) -> YoulessAPI:
    """Create a YoulessAPI client from config entry data.

    The youless_api library only sends HTTP Basic auth when the ``username``
    argument is not ``None`` - passing ``None`` disables auth entirely, even
    if a password was given. A YouLess LS120 only has a password field (no
    username) in its web UI, so when a password is set we still need to pass
    a (possibly empty) username, otherwise the password is silently ignored.
    """
    password = data.get(CONF_PASSWORD) or None
    username = (data.get(CONF_USERNAME) or "") if password else None
    return YoulessAPI(data[CONF_HOST], username, password)


class YoulessCoordinator(DataUpdateCoordinator[None]):
    """Fetch data from the YouLess device on a configurable interval."""

    config_entry: YoulessConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: YoulessConfigEntry,
        device: YoulessAPI,
    ) -> None:
        """Initialize the coordinator."""
        self.device = device

        # Poll interval comes from the options first, then the initial data,
        # then falls back to the default. Changing it in the options and
        # reloading the entry is what makes it take effect (see __init__.py).
        interval_seconds = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval_seconds),
        )

    async def _async_update_data(self) -> None:
        """Refresh the device data in the executor (the library is blocking)."""
        try:
            await self.hass.async_add_executor_job(self.device.update)
        except Exception as err:  # noqa: BLE001 - library raises bare requests errors
            raise UpdateFailed(f"Error communicating with YouLess: {err}") from err

        # The library swallows HTTP 401/errors and leaves the cache empty.
        # Surface that as a failed update so the entities go unavailable
        # instead of silently reporting nothing.
        if self.device.current_power_usage is None and self.device.model is None:
            raise UpdateFailed(
                "No data received from YouLess "
                "(wrong password, or device unreachable?)"
            )
