"""Sensor platform for Neakasa Litterbox."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr

from ..const import DOMAIN
from .cat_last_visit import NeakasaCatLastVisitSensor
from .cat_time_in_box_today import NeakasaCatTimeInBoxTodaySensor
from .cat_visits_today import NeakasaCatVisitsTodaySensor
from .cat_weight import NeakasaCatWeightSensor
from .last_visit import NeakasaLastVisitSensor
from .operating_state import NeakasaOperatingStateSensor
from .sand_percent import NeakasaSandPercentSensor
from .visits_today import NeakasaVisitsTodaySensor

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity import Entity
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..coordinator import (
        NeakasaDataUpdateCoordinator,
    )
    from ..data import NeakasaConfigEntry, NeakasaPayload


__all__ = [
    "NeakasaCatLastVisitSensor",
    "NeakasaCatTimeInBoxTodaySensor",
    "NeakasaCatVisitsTodaySensor",
    "NeakasaCatWeightSensor",
    "NeakasaLastVisitSensor",
    "NeakasaOperatingStateSensor",
    "NeakasaSandPercentSensor",
    "NeakasaVisitsTodaySensor",
]


def _device_sensors(
    coordinator: NeakasaDataUpdateCoordinator,
    iot_id: str,
) -> list[Entity]:
    """Return the per-device sensor entities for a freshly discovered device."""
    return [
        NeakasaSandPercentSensor(coordinator, iot_id),
        NeakasaOperatingStateSensor(coordinator, iot_id),
        NeakasaVisitsTodaySensor(coordinator, iot_id),
        NeakasaLastVisitSensor(coordinator, iot_id),
    ]


def _cat_sensors(
    coordinator: NeakasaDataUpdateCoordinator,
    iot_id: str,
    cat_id: int,
) -> list[Entity]:
    """Return the per-cat sensor entities for a freshly discovered cat."""
    return [
        NeakasaCatWeightSensor(coordinator, iot_id, cat_id),
        NeakasaCatLastVisitSensor(coordinator, iot_id, cat_id),
        NeakasaCatVisitsTodaySensor(coordinator, iot_id, cat_id),
        NeakasaCatTimeInBoxTodaySensor(coordinator, iot_id, cat_id),
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NeakasaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities, including dynamic discovery of new devices/cats."""
    coordinator = entry.runtime_data.coordinator
    device_registry = dr.async_get(hass)
    known_devices: set[str] = set()
    known_cats: set[tuple[str, int]] = set()

    @callback
    def _async_check_new() -> None:
        payload: NeakasaPayload | None = coordinator.data
        if payload is None:
            return
        new: list[Entity] = []
        for snap in payload.devices.values():
            iot_id = snap.device["iot_id"]
            if iot_id not in known_devices:
                known_devices.add(iot_id)
                # A child device can only be created under a registered parent.
                device_registry.async_get_or_create(
                    config_entry_id=entry.entry_id,
                    identifiers={(DOMAIN, iot_id)},
                )
                new.extend(_device_sensors(coordinator, iot_id))
            for cat in snap.cats:
                key = (iot_id, cat.id)
                if key not in known_cats:
                    known_cats.add(key)
                    new.extend(_cat_sensors(coordinator, iot_id, cat.id))
        if new:
            async_add_entities(new)

    entry.async_on_unload(coordinator.async_add_listener(_async_check_new))
    _async_check_new()
