"""Visits-today sensor for a specific cat on a Neakasa litter box."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorStateClass

from ..entity import NeakasaCatEntity

if TYPE_CHECKING:
    from ..data import NeakasaPayload


class NeakasaCatVisitsTodaySensor(NeakasaCatEntity, SensorEntity):
    """Number of visits this cat made since the start of the local day."""

    _attr_translation_key = "cat_visits_today"
    _attr_icon = "mdi:paw"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_cat_{self.cat_id}_visits_today"

    @property
    def native_value(self) -> int | None:
        """Return the visit count for this cat since midnight."""
        payload: NeakasaPayload | None = self.coordinator.data
        if payload is None:
            return None
        device = payload.devices.get(self.iot_id)
        if device is None:
            return None
        stats = device.cat_stats.get(self.cat_id)
        return None if stats is None else stats["visits_today"]
