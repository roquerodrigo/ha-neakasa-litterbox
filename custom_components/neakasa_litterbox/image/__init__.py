"""Image platform for Neakasa Litterbox."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import callback

from .cat_photo import NeakasaCatPhotoImage

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import NeakasaConfigEntry, NeakasaPayload


__all__ = ["NeakasaCatPhotoImage"]


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: NeakasaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one photo per cat, including cats discovered later."""
    coordinator = entry.runtime_data.coordinator
    known_cats: set[tuple[str, int]] = set()

    @callback
    def _async_check_new() -> None:
        payload: NeakasaPayload | None = coordinator.data
        if payload is None:
            return
        new: list[NeakasaCatPhotoImage] = []
        for snap in payload.devices.values():
            iot_id = snap.device["iot_id"]
            for cat in snap.cats:
                key = (iot_id, cat.id)
                if key not in known_cats:
                    known_cats.add(key)
                    new.append(NeakasaCatPhotoImage(coordinator, iot_id, cat.id))
        if new:
            async_add_entities(new)

    entry.async_on_unload(coordinator.async_add_listener(_async_check_new))
    _async_check_new()
