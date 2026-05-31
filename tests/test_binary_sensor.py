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


def test_bucket_full_on_when_device_reports_full(
    sample_device, sample_status, sample_cat
):
    status = dataclasses.replace(sample_status, bucket_full=True)
    snap = _snapshot(sample_device, status, sample_cat)
    s = NeakasaBucketFullBinarySensor(_coord(snap), sample_device.iot_id)
    assert s.is_on is True


def test_bucket_full_off_when_device_reports_empty(
    sample_device, sample_status, sample_cat
):
    status = dataclasses.replace(sample_status, bucket_full=False)
    snap = _snapshot(sample_device, status, sample_cat)
    s = NeakasaBucketFullBinarySensor(_coord(snap), sample_device.iot_id)
    assert s.is_on is False


def test_bucket_full_none_without_snapshot(sample_device):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    s = NeakasaBucketFullBinarySensor(coord, sample_device.iot_id)
    assert s.is_on is None
