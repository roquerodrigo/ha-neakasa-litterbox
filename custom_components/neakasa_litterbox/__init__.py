"""Neakasa Litterbox integration for Home Assistant."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, cast

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.loader import async_get_loaded_integration

from .activity_record_tracker import NeakasaActivityRecordTracker
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
from .services import async_setup_services
from .session_store import NeakasaSessionStore
from .stale_cat_devices import async_remove_stale_cat_devices

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceEntry
    from homeassistant.helpers.typing import ConfigType

    from .data import NeakasaConfigData, NeakasaConfigEntry

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.IMAGE,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:  # noqa: ARG001 - signature fixed by Home Assistant
    """Register the service actions, which outlive any single config entry."""
    async_setup_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NeakasaConfigEntry,
) -> bool:
    """Set up the Neakasa Litterbox integration from a config entry."""
    config = cast("NeakasaConfigData", entry.data)
    session_store = NeakasaSessionStore(
        hass,
        entry.entry_id,
        username=config["username"],
        region=config["region"],
    )
    client = NeakasaApiClient(
        username=config["username"],
        password=config["password"],
        region=config["region"],
        session_listener=session_store.async_schedule_save,
    )
    # Registered before any await so the SDK session is closed even when
    # setup fails later (Home Assistant runs the on_unload callbacks on a
    # failed setup too); otherwise every ConfigEntryNotReady retry would
    # leak one aiohttp session.
    entry.async_on_unload(client.async_close)
    entry.async_on_unload(session_store.async_save)
    try:
        await client.async_login(cached=await session_store.async_load())
    except NeakasaApiClientAuthenticationError as exc:
        raise ConfigEntryAuthFailed(str(exc)) from exc
    except NeakasaApiClientError as exc:
        raise ConfigEntryNotReady(str(exc)) from exc

    scan_interval = timedelta(
        seconds=scan_interval_from_options(dict(entry.options)),
    )
    coordinator = NeakasaDataUpdateCoordinator(
        hass=hass,
        entry=entry,
        scan_interval=scan_interval,
    )
    push = NeakasaPushClient(
        hass=hass,
        entry=entry,
        api=client,
        coordinator=coordinator,
    )

    activity_record_tracker = NeakasaActivityRecordTracker(hass, entry.entry_id)
    await activity_record_tracker.async_load()

    entry.runtime_data = NeakasaData(
        client=client,
        coordinator=coordinator,
        integration=async_get_loaded_integration(hass, entry.domain),
        push=push,
        activity_record_tracker=activity_record_tracker,
    )

    await coordinator.async_config_entry_first_refresh()
    push.async_start()
    entry.async_on_unload(push.async_stop)
    entry.async_on_unload(activity_record_tracker.async_save)

    async_remove_stale_cat_devices(hass, entry)
    entry.async_on_unload(
        coordinator.async_add_listener(
            lambda: async_remove_stale_cat_devices(hass, entry)
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: NeakasaConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(
    hass: HomeAssistant,
    entry: NeakasaConfigEntry,
) -> None:
    """Delete what the integration stored for an entry being removed."""
    config = cast("NeakasaConfigData", entry.data)
    await NeakasaActivityRecordTracker(hass, entry.entry_id).async_remove()
    await NeakasaSessionStore(
        hass,
        entry.entry_id,
        username=config["username"],
        region=config["region"],
    ).async_remove()


async def async_remove_config_entry_device(
    hass: HomeAssistant,  # noqa: ARG001 - signature fixed by Home Assistant
    entry: NeakasaConfigEntry,
    device_entry: DeviceEntry,
) -> bool:
    """
    Let the user delete a litter box or a cat the cloud no longer reports.

    A litter box unpaired from the account keeps its device, and its cats,
    until someone removes it. Devices still reported stay protected: their
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
