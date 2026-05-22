from __future__ import annotations

import dataclasses
from unittest.mock import MagicMock

from custom_components.neakasa_litterbox.binary_sensor.bucket_full import (
    NeakasaBucketFullBinarySensor,
)
from custom_components.neakasa_litterbox.binary_sensor.needs_cleaning import (
    NeakasaNeedsCleaningBinarySensor,
)
from custom_components.neakasa_litterbox.data import (
    NeakasaDeviceSnapshot,
    NeakasaPayload,
)


def _coord(snap: NeakasaDeviceSnapshot) -> MagicMock:
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={snap.device["iot_id"]: snap})
    coord.last_update_success = True
    return coord


def _snapshot(sample_device, sample_status, sample_cat) -> NeakasaDeviceSnapshot:
    return NeakasaDeviceSnapshot(
        device={
            "iot_id": sample_device.iot_id,
            "device_name": sample_device.device_name,
            "product_name": sample_device.product_name,
            "firmware_version": sample_status.firmware_version,
            "hardware_version": sample_status.hardware_version,
        },
        status=sample_status,
        cats=(sample_cat,),
        visits_today=0,
        last_visit_at=None,
        cat_stats={},
    )


async def test_setup_creates_two_binary_sensors(hass, setup_integration):
    assert len(hass.states.async_all("binary_sensor")) == 2


def test_needs_cleaning(sample_device, sample_status, sample_cat):
    status = dataclasses.replace(sample_status, needs_cleaning=True)
    snap = _snapshot(sample_device, status, sample_cat)
    s = NeakasaNeedsCleaningBinarySensor(_coord(snap), sample_device.iot_id)
    assert s.is_on is True


def test_needs_cleaning_none_without_snapshot(sample_device):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    s = NeakasaNeedsCleaningBinarySensor(coord, sample_device.iot_id)
    assert s.is_on is None


def test_needs_cleaning_cleared_when_clean_runs_after_visit(
    sample_device, sample_status, sample_cat
):
    # Device still reports ``catLeft.needClean == 1`` because the
    # firmware only refreshes that field on cat exit. The clean cycle
    # timestamp is newer than the last visit, so the sensor should treat
    # the box as clean.
    status = dataclasses.replace(sample_status, needs_cleaning=True)
    snap = dataclasses.replace(
        _snapshot(sample_device, status, sample_cat),
        last_visit_at=1_700_000_000,
        last_clean_at=1_700_000_500,
    )
    s = NeakasaNeedsCleaningBinarySensor(_coord(snap), sample_device.iot_id)
    assert s.is_on is False


def test_needs_cleaning_still_on_when_visit_after_clean(
    sample_device, sample_status, sample_cat
):
    status = dataclasses.replace(sample_status, needs_cleaning=True)
    snap = dataclasses.replace(
        _snapshot(sample_device, status, sample_cat),
        last_visit_at=1_700_000_500,
        last_clean_at=1_700_000_000,
    )
    s = NeakasaNeedsCleaningBinarySensor(_coord(snap), sample_device.iot_id)
    assert s.is_on is True


def test_needs_cleaning_honors_device_false_regardless_of_history(
    sample_device, sample_status, sample_cat
):
    status = dataclasses.replace(sample_status, needs_cleaning=False)
    snap = dataclasses.replace(
        _snapshot(sample_device, status, sample_cat),
        last_visit_at=1_700_000_500,
        last_clean_at=1_700_000_000,
    )
    s = NeakasaNeedsCleaningBinarySensor(_coord(snap), sample_device.iot_id)
    assert s.is_on is False


def test_bucket_full_promotes_when_window_fills_with_true(
    sample_device, sample_status, sample_cat
):
    status = dataclasses.replace(sample_status, bucket_full=True)
    snap = _snapshot(sample_device, status, sample_cat)
    coord = _coord(snap)
    s = NeakasaBucketFullBinarySensor(coord, sample_device.iot_id)
    s.hass = MagicMock()

    base = 1_000_000.0
    # Backfill once-per-second so the oldest sample after the trim is
    # exactly _WINDOW_SECONDS old.
    s._samples.extend((base + i, True) for i in range(600))

    import time

    real_monotonic = time.monotonic
    try:
        time.monotonic = lambda: base + 600
        s._evaluate()
    finally:
        time.monotonic = real_monotonic

    assert s.is_on is True


def test_bucket_full_does_not_promote_before_window_fills(
    sample_device, sample_status, sample_cat
):
    status = dataclasses.replace(sample_status, bucket_full=True)
    snap = _snapshot(sample_device, status, sample_cat)
    coord = _coord(snap)
    s = NeakasaBucketFullBinarySensor(coord, sample_device.iot_id)
    s.hass = MagicMock()

    s._evaluate()
    # Only one sample collected — far from the 5-min span requirement.
    assert s.is_on is False


def test_bucket_full_clears_immediately_on_false(
    sample_device, sample_status, sample_cat
):
    full_status = dataclasses.replace(sample_status, bucket_full=True)
    snap_full = _snapshot(sample_device, full_status, sample_cat)
    coord = _coord(snap_full)
    s = NeakasaBucketFullBinarySensor(coord, sample_device.iot_id)
    s.hass = MagicMock()
    s._stable_on = True  # simulate already-confirmed

    empty_status = dataclasses.replace(sample_status, bucket_full=False)
    snap_empty = _snapshot(sample_device, empty_status, sample_cat)
    coord.data = NeakasaPayload(devices={snap_empty.device["iot_id"]: snap_empty})
    s._evaluate()

    assert s.is_on is False


def test_bucket_full_majority_true_promotes_despite_flaps(
    sample_device, sample_status, sample_cat
):
    status = dataclasses.replace(sample_status, bucket_full=True)
    snap = _snapshot(sample_device, status, sample_cat)
    coord = _coord(snap)
    s = NeakasaBucketFullBinarySensor(coord, sample_device.iot_id)
    s.hass = MagicMock()

    base = 1_000_000.0
    # 80% True / 20% False over a span comfortably > 300s.
    for i in range(600):
        s._samples.append((base + i, i % 10 < 8))

    import time

    real_monotonic = time.monotonic
    try:
        time.monotonic = lambda: base + 600
        s._evaluate()
    finally:
        time.monotonic = real_monotonic

    assert s.is_on is True


def test_bucket_full_minority_true_stays_off(sample_device, sample_status, sample_cat):
    status = dataclasses.replace(sample_status, bucket_full=False)
    snap = _snapshot(sample_device, status, sample_cat)
    coord = _coord(snap)
    s = NeakasaBucketFullBinarySensor(coord, sample_device.iot_id)
    s.hass = MagicMock()

    base = 1_000_000.0
    # 30% True / 70% False over a span comfortably > 300s.
    for i in range(600):
        s._samples.append((base + i, i % 10 < 3))

    import time

    real_monotonic = time.monotonic
    try:
        time.monotonic = lambda: base + 600
        s._evaluate()
    finally:
        time.monotonic = real_monotonic

    assert s.is_on is False


def test_bucket_full_none_without_snapshot(sample_device):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    s = NeakasaBucketFullBinarySensor(coord, sample_device.iot_id)
    assert s.is_on is None
