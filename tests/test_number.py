from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from custom_components.neakasa_litterbox.data import (
    NeakasaDeviceSnapshot,
    NeakasaPayload,
)
from custom_components.neakasa_litterbox.number.calibrate_sand import (
    NeakasaCalibrateSandNumber,
)


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


def _coord(snap: NeakasaDeviceSnapshot, client: MagicMock) -> MagicMock:
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={snap.device["iot_id"]: snap})
    coord.last_update_success = True
    coord.async_request_refresh = AsyncMock()
    coord.config_entry.runtime_data.client = client
    return coord


async def test_setup_creates_one_number(hass, setup_integration):
    assert len(hass.states.async_all("number")) == 1


def test_calibrate_value_mirrors_sand_percent(sample_device, sample_status, sample_cat):
    snap = _snapshot(sample_device, sample_status, sample_cat)
    n = NeakasaCalibrateSandNumber(_coord(snap, MagicMock()), sample_device.iot_id)
    assert n.native_value == sample_status.sand_percent
    assert n.unique_id == f"{sample_device.iot_id}_calibrate_sand"


def test_calibrate_value_none_without_snapshot(sample_device):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    n = NeakasaCalibrateSandNumber(coord, sample_device.iot_id)
    assert n.native_value is None


async def test_calibrate_set_value_calls_client(
    sample_device, sample_status, sample_cat
):
    snap = _snapshot(sample_device, sample_status, sample_cat)
    client = MagicMock()
    client.async_calibrate_sand = AsyncMock()
    coord = _coord(snap, client)
    n = NeakasaCalibrateSandNumber(coord, sample_device.iot_id)
    await n.async_set_native_value(75)
    client.async_calibrate_sand.assert_awaited_with(sample_device.device_name, 75)
    new_payload = coord.async_set_updated_data.call_args.args[0]
    assert new_payload.devices[sample_device.iot_id].status.sand_percent == 75
    coord.async_request_refresh.assert_not_awaited()


async def test_calibrate_set_value_no_op_without_snapshot(sample_device):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    coord.async_request_refresh = AsyncMock()
    coord.config_entry.runtime_data.client = MagicMock()
    n = NeakasaCalibrateSandNumber(coord, sample_device.iot_id)
    await n.async_set_native_value(50)
    coord.async_request_refresh.assert_not_awaited()
