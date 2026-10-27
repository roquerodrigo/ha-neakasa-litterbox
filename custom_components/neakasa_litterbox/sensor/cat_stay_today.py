"""Total time spent in the litter box today, derived from cloud visit records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import UnitOfTime

from ..entity import NeakasaCatEntity

if TYPE_CHECKING:
    from ..data import NeakasaPayload


class NeakasaCatStayTodaySensor(NeakasaCatEntity, SensorEntity):
    """Aggregate today's visit durations without Home Assistant helpers."""

    _attr_name = "Stay today"
    _attr_icon = "mdi:clock-outline"
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        """Return a stable entity identifier."""
        return f"{self.iot_id}_cat_{self.cat_id}_stay_today"

    @property
    def native_value(self) -> int | None:
        """Return the sum of today's completed visit durations in seconds."""
        payload: NeakasaPayload | None = self.coordinator.data
        if payload is None:
            return None
        device = payload.devices.get(self.iot_id)
        if device is None:
            return None
        stats = device.cat_stats.get(self.cat_id)
        return None if stats is None else stats["stay_today_seconds"]
