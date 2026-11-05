"""Removal of the cat devices the cloud stopped reporting."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, LOGGER
from .device_identity import cat_identifier

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import NeakasaConfigEntry, NeakasaPayload


@callback
def async_remove_stale_cat_devices(
    hass: HomeAssistant,
    entry: NeakasaConfigEntry,
) -> None:
    """
    Delete the cat devices a reported litter box no longer lists.

    A cat deleted in the mobile app disappears from its litter box's cat list,
    and its device goes away with its entities. Only litter boxes the cloud
    still reports are checked: an unpaired box keeps its cats until the user
    deletes the box, which takes them along.
    """
    payload: NeakasaPayload | None = entry.runtime_data.coordinator.data
    if payload is None:
        return
    registry = dr.async_get(hass)
    for iot_id, snapshot in payload.devices.items():
        litter_box = registry.async_get_device_by_identifier(
            (DOMAIN, iot_id), entry.entry_id
        )
        if litter_box is None:
            continue
        reported = {cat_identifier(iot_id, cat.id) for cat in snapshot.cats}
        for cat_device in dr.async_entries_for_parent_device(registry, litter_box.id):
            if any(
                domain == DOMAIN and identifier in reported
                for domain, identifier in cat_device.identifiers
            ):
                continue
            LOGGER.debug(
                "Removing cat device %s, no longer reported by litter box %s",
                cat_device.name,
                iot_id,
            )
            registry.async_remove_device(cat_device.id)
