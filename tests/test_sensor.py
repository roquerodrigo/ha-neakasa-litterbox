from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from custom_components.neakasa_litterbox.data import (
    NeakasaDeviceSnapshot,
    NeakasaPayload,
)
from custom_components.neakasa_litterbox.sensor.cat_last_visit import (
    NeakasaCatLastVisitSensor,
)
from custom_components.neakasa_litterbox.sensor.cat_visits_today import (
    NeakasaCatVisitsTodaySensor,
)
from custom_components.neakasa_litterbox.sensor.cat_weight import NeakasaCatWeightSensor
from custom_components.neakasa_litterbox.sensor.last_visit import NeakasaLastVisitSensor
from custom_components.neakasa_litterbox.sensor.sand_percent import (
    NeakasaSandPercentSensor,
)
from custom_components.neakasa_litterbox.sensor.visits_today import (
    NeakasaVisitsTodaySensor,
)


def _coord_with(snap: NeakasaDeviceSnapshot) -> MagicMock:
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={snap.device["iot_id"]: snap})
    coord.last_update_success = True
    return coord


def _make_snapshot(
    sample_device,
    sample_status,
    sample_cat,
    *,
    visits_today=2,
    last_visit_at=1_700_000_500,
    cat_stats=None,
) -> NeakasaDeviceSnapshot:
    if cat_stats is None:
        cat_stats = {
            sample_cat.id: {
                "last_visit_at": 1_700_000_500,
                "last_visit_weight": 4.65,
                "visits_today": 3,
            },
        }
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
        visits_today=visits_today,
        last_visit_at=last_visit_at,
        cat_stats=cat_stats,
    )


async def test_setup_entry_lists_all_sensor_states(hass, setup_integration):
    states = hass.states.async_all("sensor")
    assert len(states) == 6


def test_sand_percent_native_value(sample_device, sample_status, sample_cat):
    snap = _make_snapshot(sample_device, sample_status, sample_cat)
    s = NeakasaSandPercentSensor(_coord_with(snap), sample_device.iot_id)
    assert s.native_value == sample_status.sand_percent
    assert s.unique_id == f"{sample_device.iot_id}_sand_percent"


def test_sand_percent_returns_none_when_no_snapshot(sample_device):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    s = NeakasaSandPercentSensor(coord, sample_device.iot_id)
    assert s.native_value is None


def test_visits_today_value(sample_device, sample_status, sample_cat):
    snap = _make_snapshot(sample_device, sample_status, sample_cat)
    s = NeakasaVisitsTodaySensor(_coord_with(snap), sample_device.iot_id)
    assert s.native_value == 2


def test_visits_today_none_without_snapshot(sample_device):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    s = NeakasaVisitsTodaySensor(coord, sample_device.iot_id)
    assert s.native_value is None


def test_last_visit_value(sample_device, sample_status, sample_cat):
    snap = _make_snapshot(sample_device, sample_status, sample_cat)
    s = NeakasaLastVisitSensor(_coord_with(snap), sample_device.iot_id)
    assert s.native_value == datetime.fromtimestamp(1_700_000_500, tz=UTC)


def test_last_visit_none_when_no_history(sample_device, sample_status, sample_cat):
    snap = _make_snapshot(sample_device, sample_status, sample_cat, last_visit_at=None)
    s = NeakasaLastVisitSensor(_coord_with(snap), sample_device.iot_id)
    assert s.native_value is None


def test_last_visit_none_without_snapshot(sample_device):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    s = NeakasaLastVisitSensor(coord, sample_device.iot_id)
    assert s.native_value is None


def test_cat_weight_returns_latest_visit_weight(
    sample_device, sample_status, sample_cat
):
    snap = _make_snapshot(
        sample_device,
        sample_status,
        sample_cat,
        cat_stats={
            sample_cat.id: {
                "last_visit_at": 1_700_000_500,
                "last_visit_weight": 4.65,
                "visits_today": 3,
            },
        },
    )
    s = NeakasaCatWeightSensor(_coord_with(snap), sample_device.iot_id, sample_cat.id)
    assert s.native_value == 4.65
    assert s.unique_id.endswith("_weight")


def test_cat_weight_none_without_payload(sample_device, sample_cat):
    coord = MagicMock()
    coord.data = None
    coord.last_update_success = True
    s = NeakasaCatWeightSensor(coord, sample_device.iot_id, sample_cat.id)
    assert s.native_value is None


def test_cat_weight_none_when_device_missing(sample_device, sample_cat):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    s = NeakasaCatWeightSensor(coord, sample_device.iot_id, sample_cat.id)
    assert s.native_value is None


def test_cat_weight_none_when_stats_missing(sample_device, sample_status, sample_cat):
    snap = _make_snapshot(sample_device, sample_status, sample_cat, cat_stats={})
    s = NeakasaCatWeightSensor(_coord_with(snap), sample_device.iot_id, sample_cat.id)
    assert s.native_value is None


def test_cat_last_visit(sample_device, sample_status, sample_cat):
    snap = _make_snapshot(sample_device, sample_status, sample_cat)
    s = NeakasaCatLastVisitSensor(
        _coord_with(snap), sample_device.iot_id, sample_cat.id
    )
    assert s.native_value == datetime.fromtimestamp(1_700_000_500, tz=UTC)


def test_cat_last_visit_none_without_payload(sample_device, sample_cat):
    coord = MagicMock()
    coord.data = None
    coord.last_update_success = True
    s = NeakasaCatLastVisitSensor(coord, sample_device.iot_id, sample_cat.id)
    assert s.native_value is None


def test_cat_last_visit_none_without_device(sample_device, sample_cat):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    s = NeakasaCatLastVisitSensor(coord, sample_device.iot_id, sample_cat.id)
    assert s.native_value is None


def test_cat_last_visit_none_when_stats_missing(
    sample_device, sample_status, sample_cat
):
    snap = _make_snapshot(sample_device, sample_status, sample_cat, cat_stats={})
    s = NeakasaCatLastVisitSensor(
        _coord_with(snap), sample_device.iot_id, sample_cat.id
    )
    assert s.native_value is None


def test_cat_visits_today(sample_device, sample_status, sample_cat):
    snap = _make_snapshot(sample_device, sample_status, sample_cat)
    s = NeakasaCatVisitsTodaySensor(
        _coord_with(snap), sample_device.iot_id, sample_cat.id
    )
    assert s.native_value == 3


def test_cat_visits_today_none_without_payload(sample_device, sample_cat):
    coord = MagicMock()
    coord.data = None
    coord.last_update_success = True
    s = NeakasaCatVisitsTodaySensor(coord, sample_device.iot_id, sample_cat.id)
    assert s.native_value is None


def test_cat_visits_today_none_when_stats_missing(
    sample_device, sample_status, sample_cat
):
    snap = _make_snapshot(sample_device, sample_status, sample_cat, cat_stats={})
    s = NeakasaCatVisitsTodaySensor(
        _coord_with(snap), sample_device.iot_id, sample_cat.id
    )
    assert s.native_value is None


def test_cat_visits_today_none_without_device(sample_device, sample_cat):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    s = NeakasaCatVisitsTodaySensor(coord, sample_device.iot_id, sample_cat.id)
    assert s.native_value is None
