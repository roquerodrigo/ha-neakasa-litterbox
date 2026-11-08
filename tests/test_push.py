from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from neakasa_litterbox_sdk import NeakasaError, StatusUpdate
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.neakasa_litterbox.const import DOMAIN
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
async def push_setup(hass, sample_device, sample_status, sample_cat):
    snap = _snapshot(sample_device, sample_status, sample_cat)
    payload = NeakasaPayload(devices={snap.device["iot_id"]: snap})
    coordinator = MagicMock()
    coordinator.data = payload
    coordinator.async_set_updated_data = MagicMock()
    coordinator.async_request_refresh = AsyncMock()
    stream = MagicMock()
    stream.start = AsyncMock()
    stream.stop = AsyncMock()
    api = MagicMock()
    api.watch_status = MagicMock(return_value=stream)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    push = NeakasaPushClient(hass=hass, entry=entry, api=api, coordinator=coordinator)
    yield push, api, stream, coordinator, snap, entry
    # Cancel the reconnect supervisor so it doesn't outlive the test.
    await push.async_stop()


async def _settle(hass):
    for _ in range(10):
        await asyncio.sleep(0)
    await hass.async_block_till_done()


async def _start(hass, push):
    push.async_start()
    await _settle(hass)


async def test_start_opens_stream_in_background(hass, push_setup):
    push, _, stream, *_ = push_setup
    connected = asyncio.Event()

    async def connect() -> None:
        await connected.wait()

    stream.start = AsyncMock(side_effect=connect)
    push.async_start()
    assert push._stream is None
    connected.set()
    await _settle(hass)
    stream.start.assert_awaited_once()
    assert push._stream is stream


async def test_first_connection_does_not_refresh(hass, push_setup):
    push, _, _, coordinator, *_ = push_setup
    await _start(hass, push)
    coordinator.async_request_refresh.assert_not_awaited()


async def test_start_keeps_sdk_tls_defaults(hass, push_setup):
    # Passing anything here would mean overriding the SDK's verified
    # TLS setup for the push channel.
    push, api, *_ = push_setup
    await _start(hass, push)
    api.watch_status.assert_called_once_with()


async def test_start_registers_supervisor_as_entry_background_task(hass, push_setup):
    push, _, _, _, _, entry = push_setup
    await _start(hass, push)
    assert push._supervisor is not None
    assert push._supervisor in entry._background_tasks


async def test_stop_cancels_supervisor(hass, push_setup):
    push, *_ = push_setup
    await _start(hass, push)
    supervisor = push._supervisor
    await push.async_stop()
    assert push._supervisor is None
    assert supervisor.cancelled()


async def test_start_idempotent(hass, push_setup):
    push, _, stream, *_ = push_setup
    await _start(hass, push)
    await _start(hass, push)
    stream.start.assert_awaited_once()


async def test_start_swallows_sdk_error(hass, push_setup):
    push, _, stream, *_ = push_setup
    stream.start = AsyncMock(side_effect=NeakasaError("boom"))
    await _start(hass, push)
    assert push._stream is None
    stream.start.assert_awaited_once()


async def test_connection_after_failed_start_catches_up(hass, push_setup):
    push, _, stream, coordinator, *_ = push_setup
    stream.start = AsyncMock(side_effect=[NeakasaError("boom"), None])
    with patch("custom_components.neakasa_litterbox.push._INITIAL_BACKOFF_SECONDS", 0):
        await _start(hass, push)
    assert stream.start.await_count == 2
    assert push._stream is stream
    coordinator.async_request_refresh.assert_awaited_once()


async def test_stop_during_connection_closes_the_opened_stream(hass, push_setup):
    push, _, stream, *_ = push_setup
    connecting = asyncio.Event()

    async def hang() -> None:
        connecting.set()
        await asyncio.Event().wait()

    stream.start = AsyncMock(side_effect=hang)
    push.async_start()
    await connecting.wait()
    await push.async_stop()
    assert push._stream is None
    stream.stop.assert_awaited_once()


async def test_stop_invokes_stream_stop(hass, push_setup):
    push, _, stream, *_ = push_setup
    await _start(hass, push)
    await push.async_stop()
    stream.stop.assert_awaited_once()


async def test_stop_idempotent(push_setup):
    push, _, stream, *_ = push_setup
    await push.async_stop()
    stream.stop.assert_not_awaited()


async def test_stop_swallows_sdk_error(hass, push_setup):
    push, _, stream, *_ = push_setup
    await _start(hass, push)
    stream.stop = AsyncMock(side_effect=NeakasaError("boom"))
    await push.async_stop()
    assert push._stream is None


async def test_handle_change_updates_status(push_setup):
    push, _, _, coordinator, snap, _ = push_setup
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


async def test_handle_change_ignored_without_payload(push_setup):
    push, _, _, coordinator, _, _ = push_setup
    coordinator.data = None
    push._handle_change(
        StatusUpdate(device_name="dn-1", changes={"sand_percent": 10}),
    )
    coordinator.async_set_updated_data.assert_not_called()


async def test_handle_change_ignored_for_unknown_device(push_setup):
    push, _, _, coordinator, _, _ = push_setup
    push._handle_change(
        StatusUpdate(device_name="other", changes={"sand_percent": 5}),
    )
    coordinator.async_set_updated_data.assert_not_called()


async def test_handle_change_ignored_with_no_known_keys(push_setup):
    push, _, _, coordinator, snap, _ = push_setup
    push._handle_change(
        StatusUpdate(
            device_name=snap.device["device_name"],
            changes={"completely_unknown_key": "x"},
        ),
    )
    coordinator.async_set_updated_data.assert_not_called()
