"""The YouLess (custom) integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_HOST
from .coordinator import YoulessConfigEntry, YoulessCoordinator, build_device

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: YoulessConfigEntry) -> bool:
    """Set up YouLess (custom) from a config entry."""
    device = build_device(entry.data)

    # initialize() does a blocking HTTP call to read device/firmware info and
    # (if a password is set) to log in. Run it in the executor.
    try:
        await hass.async_add_executor_job(device.initialize)
    except Exception as err:  # noqa: BLE001 - library raises bare requests errors
        raise ConfigEntryNotReady(
            f"Unable to reach YouLess at {entry.data[CONF_HOST]}: {err}"
        ) from err

    coordinator = YoulessCoordinator(hass, entry, device)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload the entry when the options change so a new poll interval applies.
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def _async_reload_entry(
    hass: HomeAssistant, entry: YoulessConfigEntry
) -> None:
    """Reload the config entry (used when options are updated)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: YoulessConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
