"""Neakasa Litterbox integration for Home Assistant."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, cast

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.loader import async_get_loaded_integration

from .api import NeakasaApiClient
from .const import DOMAIN
from .coordinator import NeakasaDataUpdateCoordinator, scan_interval_from_options
from .data import NeakasaData
from .device_identity import live_identifiers
from .exceptions import (
    NeakasaApiClientAuthenticationError,
    NeakasaApiClientError,
)
from .push import NeakasaPushClient

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceEntry

    from .data import NeakasaConfigData, NeakasaConfigEntry

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NeakasaConfigEntry,
) -> bool:
    """Set up the Neakasa Litterbox integration from a config entry."""
    config = cast("NeakasaConfigData", entry.data)
    client = NeakasaApiClient(
        username=config["username"],
        password=config["password"],
        region=config["region"],
    )
    try:
        await client.async_login()
    except NeakasaApiClientAuthenticationError as exc:
        await client.async_close()
        raise ConfigEntryAuthFailed(str(exc)) from exc
    except NeakasaApiClientError as exc:
        await client.async_close()
        raise ConfigEntryNotReady(str(exc)) from exc

    scan_interval = timedelta(
        seconds=scan_interval_from_options(dict(entry.options)),
    )
    coordinator = NeakasaDataUpdateCoordinator(hass=hass, scan_interval=scan_interval)
    push = NeakasaPushClient(hass=hass, api=client, coordinator=coordinator)

    entry.runtime_data = NeakasaData(
        client=client,
        coordinator=coordinator,
        integration=async_get_loaded_integration(hass, entry.domain),
        push=push,
    )

    await coordinator.async_config_entry_first_refresh()
    await push.async_start()
    entry.async_on_unload(push.async_stop)
    entry.async_on_unload(client.async_close)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: NeakasaConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant,  # noqa: ARG001 - signature fixed by Home Assistant
    entry: NeakasaConfigEntry,
    device_entry: DeviceEntry,
) -> bool:
    """
    Let the user delete a litter box or a cat the cloud no longer reports.

    A cat deleted in the mobile app keeps its Home Assistant device until
    someone removes it. Devices still reported stay protected: their
    entities are recreated only on the next reload, so deleting one mid
    session would leave the integration without them.
    """
    if entry.state is not ConfigEntryState.LOADED:
        return True
    live = live_identifiers(entry.runtime_data.coordinator.data)
    return not any(
        identifier in live
        for domain, identifier in device_entry.identifiers
        if domain == DOMAIN
    )


async def async_reload_entry(
    hass: HomeAssistant,
    entry: NeakasaConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
