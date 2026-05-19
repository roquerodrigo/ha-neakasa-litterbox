from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from neakasa_litterbox_sdk import NeakasaError, StatusUpdate

from custom_components.neakasa_litterbox.data import (
    NeakasaDeviceSnapshot,
    NeakasaPayload,
)
from custom_components.neakasa_litterbox.push import NeakasaPushClient


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


@pytest.fixture
def push_setup(hass, sample_device, sample_status, sample_cat):
    snap = _snapshot(sample_device, sample_status, sample_cat)
    payload = NeakasaPayload(devices={snap.device["iot_id"]: snap})
    coordinator = MagicMock()
    coordinator.data = payload
    coordinator.async_set_updated_data = MagicMock()
    stream = MagicMock()
    stream.start = AsyncMock()
    stream.stop = AsyncMock()
    api = MagicMock()
    api.watch_status = MagicMock(return_value=stream)
    push = NeakasaPushClient(hass=hass, api=api, coordinator=coordinator)
    return push, api, stream, coordinator, snap


async def test_start_invokes_stream_start(push_setup):
    push, _, stream, *_ = push_setup
    await push.async_start()
    stream.start.assert_awaited_once()


async def test_start_idempotent(push_setup):
    push, _, stream, *_ = push_setup
    await push.async_start()
    await push.async_start()
    stream.start.assert_awaited_once()


async def test_start_swallows_sdk_error(push_setup):
    push, _, stream, *_ = push_setup
    stream.start = AsyncMock(side_effect=NeakasaError("boom"))
    await push.async_start()
    assert push._stream is None


async def test_stop_invokes_stream_stop(push_setup):
    push, _, stream, *_ = push_setup
    await push.async_start()
    await push.async_stop()
    stream.stop.assert_awaited_once()


async def test_stop_idempotent(push_setup):
    push, _, stream, *_ = push_setup
    await push.async_stop()
    stream.stop.assert_not_awaited()


async def test_stop_swallows_sdk_error(push_setup):
    push, _, stream, *_ = push_setup
    await push.async_start()
    stream.stop = AsyncMock(side_effect=NeakasaError("boom"))
    await push.async_stop()
    assert push._stream is None


def test_handle_change_updates_status(push_setup):
    push, _, _, coordinator, snap = push_setup
    update = StatusUpdate(
        device_name=snap.device["device_name"],
        changes={"sand_percent": 25, "silent_mode": True, "unknown_field": 1},
    )
    push._handle_change(update)
    coordinator.async_set_updated_data.assert_called_once()
    new_payload = coordinator.async_set_updated_data.call_args.args[0]
    new_snap = new_payload.devices[snap.device["iot_id"]]
    assert new_snap.status.sand_percent == 25
    assert new_snap.status.silent_mode is True


def test_handle_change_ignored_without_payload(push_setup):
    push, _, _, coordinator, _ = push_setup
    coordinator.data = None
    push._handle_change(
        StatusUpdate(device_name="dn-1", changes={"sand_percent": 10}),
    )
    coordinator.async_set_updated_data.assert_not_called()


def test_handle_change_ignored_for_unknown_device(push_setup):
    push, _, _, coordinator, _ = push_setup
    push._handle_change(
        StatusUpdate(device_name="other", changes={"sand_percent": 5}),
    )
    coordinator.async_set_updated_data.assert_not_called()


def test_handle_change_ignored_with_no_known_keys(push_setup):
    push, _, _, coordinator, snap = push_setup
    push._handle_change(
        StatusUpdate(
            device_name=snap.device["device_name"],
            changes={"completely_unknown_key": "x"},
        ),
    )
    coordinator.async_set_updated_data.assert_not_called()
