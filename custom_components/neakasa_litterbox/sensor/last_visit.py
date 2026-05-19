"""Last-visit timestamp sensor for a Neakasa litter box."""

from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from ..entity import NeakasaDeviceEntity


class NeakasaLastVisitSensor(NeakasaDeviceEntity, SensorEntity):
    """Timestamp of the most recent cat visit recorded for this device."""

    _attr_translation_key = "last_visit"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_last_visit"

    @property
    def native_value(self) -> datetime | None:
        """Return the timestamp of the most recent visit, or ``None``."""
        snap = self.snapshot
        if snap is None or snap.last_visit_at is None:
            return None
        return datetime.fromtimestamp(snap.last_visit_at, tz=UTC)
