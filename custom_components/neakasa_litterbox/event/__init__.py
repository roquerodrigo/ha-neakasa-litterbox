"""Event platform for Neakasa Litterbox."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import callback

from .activity import NeakasaActivityEvent

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..data import NeakasaConfigEntry, NeakasaPayload


__all__ = ["NeakasaActivityEvent"]


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: NeakasaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up event entities, dynamically tracking new devices."""
    coordinator = entry.runtime_data.coordinator
    known_devices: set[str] = set()

    @callback
    def _async_check_new() -> None:
        payload: NeakasaPayload | None = coordinator.data
        if payload is None:
            return
        new: list[NeakasaActivityEvent] = []
        for snap in payload.devices.values():
            iot_id = snap.device["iot_id"]
            if iot_id not in known_devices:
                known_devices.add(iot_id)
                new.append(NeakasaActivityEvent(coordinator, iot_id))
        if new:
            async_add_entities(new)

    entry.async_on_unload(coordinator.async_add_listener(_async_check_new))
    _async_check_new()
