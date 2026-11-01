from __future__ import annotations

from datetime import UTC, datetime, timedelta

from homeassistant.util import dt as dt_util
from neakasa_litterbox_sdk import RecordType, ToiletRecord
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.neakasa_litterbox.activity_record_tracker import (
    NeakasaActivityRecordTracker,
)

_NOW = 1_800_000_000
_IOT_ID = "iot-id-1"


def _record(
    record_id: int,
    record_type: RecordType = RecordType.CAT_VISIT,
    *,
    start_time: int = _NOW - 200,
    end_time: int = _NOW - 100,
) -> ToiletRecord:
    return ToiletRecord(
        record_id=record_id,
        record_type=record_type,
        cat_id=0,
        start_time=start_time,
        end_time=end_time,
        weight=0,
        unit="",
        way=0,
    )


def _ids(records: list[ToiletRecord]) -> list[int]:
    return [record.record_id for record in records]


def _tracker(hass, freezer) -> NeakasaActivityRecordTracker:
    freezer.move_to(datetime.fromtimestamp(_NOW, UTC))
    return NeakasaActivityRecordTracker(hass, "entry")


async def test_first_sight_of_a_device_only_seeds(hass, freezer):
    tracker = _tracker(hass, freezer)
    assert tracker.collect_new(_IOT_ID, [_record(10), _record(11)]) == []
    assert _ids(tracker.collect_new(_IOT_ID, [_record(11), _record(12)])) == [12]


async def test_empty_first_sight_does_not_hide_later_records(hass, freezer):
    tracker = _tracker(hass, freezer)
    assert tracker.collect_new(_IOT_ID, []) == []
    assert _ids(tracker.collect_new(_IOT_ID, [_record(10)])) == [10]


async def test_cursors_are_kept_per_record_type(hass, freezer):
    # Real sequences: visits around 248 million, leveling around 10 million.
    tracker = _tracker(hass, freezer)
    tracker.collect_new(
        _IOT_ID,
        [_record(248_000_000), _record(10_000_000, RecordType.OTHER)],
    )
    new_leveling = _record(10_000_001, RecordType.OTHER)
    assert _ids(tracker.collect_new(_IOT_ID, [new_leveling])) == [10_000_001]


async def test_cursors_are_kept_per_device(hass, freezer):
    tracker = _tracker(hass, freezer)
    tracker.collect_new("box-a", [_record(10)])
    tracker.collect_new("box-b", [_record(20)])
    assert _ids(tracker.collect_new("box-a", [_record(11)])) == [11]


async def test_new_records_are_returned_by_end_time(hass, freezer):
    tracker = _tracker(hass, freezer)
    tracker.collect_new(_IOT_ID, [_record(1)])
    late_visit = _record(2, end_time=_NOW - 10)
    early_cleaning = _record(3, RecordType.CLEAN_CYCLE, end_time=_NOW - 50)
    assert _ids(tracker.collect_new(_IOT_ID, [late_visit, early_cleaning])) == [3, 2]


async def test_unfinished_records_wait_until_they_end(hass, freezer):
    tracker = _tracker(hass, freezer)
    tracker.collect_new(_IOT_ID, [_record(1)])
    in_progress = _record(2, end_time=_NOW + 100)
    without_end = _record(3, end_time=0)
    assert tracker.collect_new(_IOT_ID, [in_progress, without_end]) == []
    finished = _record(2, end_time=_NOW - 1)
    assert _ids(tracker.collect_new(_IOT_ID, [finished])) == [2]


async def test_cursors_survive_a_restart(hass, hass_storage, freezer):
    tracker = _tracker(hass, freezer)
    tracker.collect_new(_IOT_ID, [_record(10)])
    await tracker.async_save()

    restarted = NeakasaActivityRecordTracker(hass, "entry")
    await restarted.async_load()

    assert _ids(restarted.collect_new(_IOT_ID, [_record(10), _record(11)])) == [11]


async def test_new_records_are_saved_without_an_explicit_call(
    hass, hass_storage, freezer
):
    tracker = _tracker(hass, freezer)
    tracker.collect_new(_IOT_ID, [_record(10)])
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=2))
    await hass.async_block_till_done()
    stored = hass_storage["neakasa_litterbox.entry.activity_records"]["data"]
    assert stored == {_IOT_ID: {"1": 10}}


async def test_remove_deletes_the_file(hass, hass_storage, freezer):
    tracker = _tracker(hass, freezer)
    tracker.collect_new(_IOT_ID, [_record(10)])
    await tracker.async_save()
    await tracker.async_remove()
    assert "neakasa_litterbox.entry.activity_records" not in hass_storage
