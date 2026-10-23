"""Regression tests for integration-native Neakasa activity and stay sensors."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from neakasa_litterbox_sdk import RecordType, ToiletRecord

from custom_components.neakasa_litterbox.coordinator import _build_snapshot
from custom_components.neakasa_litterbox.sensor.cat_stay_today import (
    NeakasaCatStayTodaySensor,
)
from custom_components.neakasa_litterbox.sensor.recent_activity import (
    NeakasaRecentActivitySensor,
)


def _record(identifier, kind, cat_id, start, end, weight=0.0, unit=""):
    return ToiletRecord(
        record_id=identifier,
        record_type=kind,
        cat_id=cat_id,
        start_time=start,
        end_time=end,
        weight=weight,
        unit=unit,
        way=0,
    )


def test_native_activity_includes_clean_and_cat_records_without_duplicates(
    sample_device, sample_status, sample_cat, monkeypatch
):
    from homeassistant.util import dt as dt_util

    fake_now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(dt_util, "utcnow", lambda: fake_now)
    monkeypatch.setattr(
        dt_util, "start_of_local_day", lambda: datetime(2026, 10, 22, tzinfo=UTC)
    )
    start = int(fake_now.timestamp()) - 1800
    visit = _record(
        1, RecordType.CAT_VISIT, sample_cat.id, start, start + 45, 4.1, "kg"
    )
    clean = _record(2, RecordType.CLEAN_CYCLE, 0, start + 60, start + 200)
    snap = _build_snapshot(
        sample_device, sample_status, [sample_cat], [visit, clean, visit]
    )
    assert snap.cat_stats[sample_cat.id]["visits_today"] == 1
    assert snap.cat_stats[sample_cat.id]["stay_today_seconds"] == 45
    assert [r.record_id for r in snap.recent_records] == [2, 1]
    assert snap.last_clean_at == clean.end_time


def test_stay_today_clips_visit_crossing_midnight(
    sample_device, sample_status, sample_cat, monkeypatch
):
    from homeassistant.util import dt as dt_util

    fake_now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    midnight = int(datetime(2026, 10, 22, tzinfo=UTC).timestamp())
    monkeypatch.setattr(dt_util, "utcnow", lambda: fake_now)
    monkeypatch.setattr(
        dt_util, "start_of_local_day", lambda: datetime.fromtimestamp(midnight, tz=UTC)
    )
    visit = _record(
        3, RecordType.CAT_VISIT, sample_cat.id, midnight - 50, midnight + 20
    )
    snap = _build_snapshot(sample_device, sample_status, [sample_cat], [visit])
    assert snap.cat_stats[sample_cat.id]["stay_today_seconds"] == 20
    assert snap.cat_stats[sample_cat.id]["visits_today"] == 0


def test_recent_activity_sensor_schema(
    sample_device, sample_status, sample_cat, monkeypatch
):
    from unittest.mock import patch

    from homeassistant.util import dt as dt_util

    now = datetime(2026, 10, 22, 12, tzinfo=UTC)
    monkeypatch.setattr(dt_util, "utcnow", lambda: now)
    monkeypatch.setattr(
        dt_util, "start_of_local_day", lambda: datetime(2026, 10, 22, tzinfo=UTC)
    )
    start = int(now.timestamp()) - 100
    visit = _record(
        11, RecordType.CAT_VISIT, sample_cat.id, start, start + 45, 4.1, "kg"
    )
    clean = _record(12, RecordType.CLEAN_CYCLE, 0, start + 50, start + 80)
    snap = _build_snapshot(sample_device, sample_status, [sample_cat], [visit, clean])
    sensor = object.__new__(NeakasaRecentActivitySensor)
    with patch.object(
        NeakasaRecentActivitySensor,
        "snapshot",
        property(lambda _self: snap),
    ):
        events = sensor.extra_state_attributes["events"]
        assert len(events) == 2
        assert events[0]["type"] == "cleaning"
        assert events[1]["cat"] == sample_cat.name
        assert events[1]["duration_seconds"] == 45
        assert events[1]["weight_unit"] == "kg"
        assert sensor.native_value == datetime.fromtimestamp(clean.start_time, tz=UTC)


def test_native_snapshot_no_records(sample_device, sample_status, sample_cat):
    snap = _build_snapshot(sample_device, sample_status, [sample_cat], [])
    assert snap.recent_records == ()
    assert snap.cat_stats[sample_cat.id]["stay_today_seconds"] == 0


def test_stay_today_sensor_reads_native_aggregate(
    sample_device, sample_status, sample_cat, monkeypatch
):
    from homeassistant.util import dt as dt_util

    from custom_components.neakasa_litterbox.data import NeakasaPayload

    now = datetime(2026, 10, 22, 12, tzinfo=UTC)
    monkeypatch.setattr(dt_util, "utcnow", lambda: now)
    monkeypatch.setattr(
        dt_util, "start_of_local_day", lambda: datetime(2026, 10, 22, tzinfo=UTC)
    )
    start = int(now.timestamp()) - 100
    visit = _record(21, RecordType.CAT_VISIT, sample_cat.id, start, start + 31)
    snap = _build_snapshot(sample_device, sample_status, [sample_cat], [visit])
    payload = NeakasaPayload(devices={sample_device.iot_id: snap})
    coordinator = MagicMock()
    coordinator.data = payload
    sensor = NeakasaCatStayTodaySensor(coordinator, sample_device.iot_id, sample_cat.id)
    assert sensor.native_value == 31


def test_recent_activity_merges_leveling_and_cleanup_completion(
    sample_device, sample_status, sample_cat, monkeypatch
):
    from dataclasses import replace
    from unittest.mock import patch

    from homeassistant.util import dt as dt_util

    now = datetime(2026, 10, 22, 12, tzinfo=UTC)
    monkeypatch.setattr(dt_util, "utcnow", lambda: now)
    monkeypatch.setattr(
        dt_util, "start_of_local_day", lambda: datetime(2026, 10, 22, tzinfo=UTC)
    )
    started = int(now.timestamp()) - 200
    clean = _record(99, RecordType.CLEAN_CYCLE, 0, started, started + 120)
    snap = _build_snapshot(sample_device, sample_status, [sample_cat], [clean])
    snap = replace(snap, leveling_events=(started + 180,))
    sensor = object.__new__(NeakasaRecentActivitySensor)
    with patch.object(
        NeakasaRecentActivitySensor,
        "snapshot",
        property(lambda _self: snap),
    ):
        events = sensor.extra_state_attributes["events"]
        assert [event["type"] for event in events] == ["leveling", "cleaning"]
        assert (
            events[1]["completed_at"]
            == datetime.fromtimestamp(clean.end_time, tz=UTC).isoformat()
        )
        assert sensor.native_value == datetime.fromtimestamp(started + 180, tz=UTC)
