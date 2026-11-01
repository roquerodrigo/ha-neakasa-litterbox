"""Activity event entity for a Neakasa litter box."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.event import EventEntity
from homeassistant.core import callback
from homeassistant.util import dt as dt_util
from neakasa_litterbox_sdk import RecordType

from ..entity import NeakasaDeviceEntity

if TYPE_CHECKING:
    from neakasa_litterbox_sdk import Cat, ToiletRecord

    from ..data import NeakasaActivityEventAttributes


_EVENT_TYPE_BY_RECORD_TYPE: dict[RecordType, str] = {
    RecordType.CAT_VISIT: "cat_visit",
    RecordType.CLEAN_CYCLE: "cleaning_completed",
    # The SDK names type 3 ``OTHER``, but each of its records matches one
    # leveling cycle reported by the ``bucketStatus`` property.
    RecordType.OTHER: "leveling_completed",
}


class NeakasaActivityEvent(NeakasaDeviceEntity, EventEntity):
    """Fires once for each visit, cleaning or leveling the cloud records."""

    _attr_translation_key = "activity"
    _attr_icon = "mdi:history"

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_activity"

    @property
    def event_types(self) -> list[str]:
        """Return the kinds of activity this entity reports."""
        return list(_EVENT_TYPE_BY_RECORD_TYPE.values())

    async def async_added_to_hass(self) -> None:
        """Report what happened while Home Assistant was not running."""
        await super().async_added_to_hass()
        self._report_new_records()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Report new records before writing the regular state update."""
        self._report_new_records()
        super()._handle_coordinator_update()

    def _report_new_records(self) -> None:
        """Fire one event per record the tracker has not seen yet."""
        snap = self.snapshot
        if snap is None:
            return
        tracker = self.coordinator.config_entry.runtime_data.activity_record_tracker
        for record in tracker.collect_new(self.iot_id, snap.activity_records):
            self._trigger_event(
                _EVENT_TYPE_BY_RECORD_TYPE[record.record_type],
                dict(_event_attributes(record, snap.cats)),
            )
            self.async_write_ha_state()


def _event_attributes(
    record: ToiletRecord,
    cats: tuple[Cat, ...],
) -> NeakasaActivityEventAttributes:
    """Describe a record, with the time it happened rather than when it arrived."""
    attributes: NeakasaActivityEventAttributes = {
        "record_id": record.record_id,
        "started_at": dt_util.utc_from_timestamp(record.start_time).isoformat(),
        "ended_at": dt_util.utc_from_timestamp(record.end_time).isoformat(),
        "duration_seconds": record.duration_seconds,
    }
    if record.record_type is RecordType.CAT_VISIT:
        attributes["cat_id"] = record.cat_id or None
        attributes["cat_name"] = next(
            (cat.name for cat in cats if cat.id == record.cat_id),
            None,
        )
        attributes["weight"] = record.weight
        attributes["weight_unit"] = record.unit
    return attributes
