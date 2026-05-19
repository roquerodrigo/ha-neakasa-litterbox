"""Last-visit timestamp sensor for a specific cat on a Neakasa litter box."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from ..entity import NeakasaCatEntity

if TYPE_CHECKING:
    from ..data import NeakasaPayload


class NeakasaCatLastVisitSensor(NeakasaCatEntity, SensorEntity):
    """Timestamp of this cat's most recent visit within the lookback window."""

    _attr_translation_key = "cat_last_visit"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_cat_{self.cat_id}_last_visit"

    @property
    def native_value(self) -> datetime | None:
        """Return the timestamp of this cat's latest visit, or ``None``."""
        payload: NeakasaPayload | None = self.coordinator.data
        if payload is None:
            return None
        device = payload.devices.get(self.iot_id)
        if device is None:
            return None
        stats = device.cat_stats.get(self.cat_id)
        if stats is None or stats["last_visit_at"] is None:
            return None
        return datetime.fromtimestamp(stats["last_visit_at"], tz=UTC)
