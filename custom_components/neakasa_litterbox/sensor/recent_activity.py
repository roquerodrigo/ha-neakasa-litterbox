"""Structured visit and cleanup history exposed by the Neakasa cloud."""

from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from neakasa_litterbox_sdk import RecordType

from ..entity import NeakasaDeviceEntity


class NeakasaRecentActivitySensor(NeakasaDeviceEntity, SensorEntity):
    """Expose a bounded, read-only activity timeline for Lovelace cards."""

    _attr_name = "Recent activity"
    _attr_icon = "mdi:history"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def unique_id(self) -> str:
        """Return a stable entity identifier."""
        return f"{self.iot_id}_recent_activity"

    @property
    def native_value(self) -> datetime | None:
        """Return the most recent recorded event timestamp."""
        snap = self.snapshot
        if snap is None:
            return None
        latest = max(
            (record.start_time for record in snap.recent_records),
            default=0,
        )
        latest = max(latest, max(snap.leveling_events, default=0))
        return datetime.fromtimestamp(latest, tz=UTC) if latest else None

    @property
    def extra_state_attributes(self) -> dict[str, list[dict[str, object]]]:
        """Return structured records with cat identity and durations."""
        snap = self.snapshot
        if snap is None:
            return {"events": []}
        cat_names = {cat.id: cat.name for cat in snap.cats}
        events: list[dict[str, object]] = []
        for record in snap.recent_records:
            kind = (
                "cat_visit"
                if record.record_type == RecordType.CAT_VISIT
                else "cleaning"
            )
            event: dict[str, object] = {
                "id": record.record_id,
                "type": kind,
                "timestamp": datetime.fromtimestamp(
                    record.start_time, tz=UTC
                ).isoformat(),
                "duration_seconds": max(0, record.duration_seconds),
                "completed_at": datetime.fromtimestamp(
                    record.end_time, tz=UTC
                ).isoformat(),
            }
            if kind == "cat_visit":
                event["cat"] = cat_names.get(record.cat_id, "Unknown")
                event["cat_id"] = record.cat_id
                if record.weight > 0:
                    event["weight"] = record.weight
                    event["weight_unit"] = record.unit or "kg"
            events.append(event)
        events.extend(
            {
                "id": f"leveling-{timestamp}",
                "type": "leveling",
                "timestamp": datetime.fromtimestamp(timestamp, tz=UTC).isoformat(),
                "completed_at": datetime.fromtimestamp(timestamp, tz=UTC).isoformat(),
                "duration_seconds": snap.leveling_durations.get(timestamp, 0),
            }
            for timestamp in snap.leveling_events
        )
        events.sort(key=lambda event: str(event["timestamp"]), reverse=True)
        return {"events": events[:30]}
