from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from neakasa_litterbox_sdk import NeakasaError, OperatingState, StatusUpdate
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
    coordinator.leveling_events = {}
    coordinator.leveling_durations = {}
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


async def test_start_invokes_stream_start(push_setup):
    push, _, stream, *_ = push_setup
    await push.async_start()
    stream.start.assert_awaited_once()


async def test_start_keeps_sdk_tls_defaults(push_setup):
    # Passing anything here would mean overriding the SDK's verified
    # TLS setup for the push channel.
    push, api, *_ = push_setup
    await push.async_start()
    api.watch_status.assert_called_once_with()


async def test_start_registers_supervisor_as_entry_background_task(push_setup):
    push, _, _, _, _, entry = push_setup
    await push.async_start()
    assert push._supervisor is not None
    assert push._supervisor in entry._background_tasks


async def test_stop_cancels_supervisor(push_setup):
    push, *_ = push_setup
    await push.async_start()
    supervisor = push._supervisor
    await push.async_stop()
    assert push._supervisor is None
    assert supervisor.cancelled() or supervisor.cancelling()


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


async def test_transient_leveling_to_idle_does_not_create_completion(push_setup, hass):
    from dataclasses import replace
    from unittest.mock import patch

    push, _, _, coordinator, snap, _ = push_setup
    leveling_status = replace(snap.status, operating_state=OperatingState.LEVELING)
    leveling_snap = replace(snap, status=leveling_status)
    coordinator.data = NeakasaPayload(devices={snap.device["iot_id"]: leveling_snap})
    with patch.object(
        push._leveling_store, "async_save", new_callable=AsyncMock
    ) as save:
        push._handle_change(
            StatusUpdate(
                device_name=snap.device["device_name"],
                changes={"operating_state": OperatingState.IDLE},
            )
        )
        await hass.async_block_till_done()
        save.assert_not_awaited()
    assert coordinator.leveling_events == {}
    result = coordinator.async_set_updated_data.call_args.args[0]
    assert result.devices[snap.device["iot_id"]].leveling_events == ()


async def test_sustained_leveling_records_measured_duration(push_setup, hass):
    from unittest.mock import patch

    push, _, _, coordinator, snap, _ = push_setup
    coordinator.data = NeakasaPayload(devices={snap.device["iot_id"]: snap})
    with (
        patch(
            "custom_components.neakasa_litterbox.push.time.time",
            side_effect=[1000.0, 1040.0],
        ),
        patch.object(push._leveling_store, "async_save", new_callable=AsyncMock),
        patch.object(push._duration_store, "async_save", new_callable=AsyncMock),
    ):
        push._handle_change(
            StatusUpdate(
                device_name=snap.device["device_name"],
                changes={"operating_state": OperatingState.LEVELING},
            )
        )
        leveling_snapshot = coordinator.async_set_updated_data.call_args.args[0]
        coordinator.data = leveling_snapshot
        push._handle_change(
            StatusUpdate(
                device_name=snap.device["device_name"],
                changes={"operating_state": OperatingState.IDLE},
            )
        )
        await hass.async_block_till_done()
    assert coordinator.leveling_events[snap.device["iot_id"]] == [1040]
    assert coordinator.leveling_durations[snap.device["iot_id"]][1040] == 40
    latest = coordinator.async_set_updated_data.call_args.args[0]
    assert latest.devices[snap.device["iot_id"]].leveling_durations[1040] == 40


async def test_poll_leveling_then_mqtt_idle_records_completion(push_setup, hass):
    from unittest.mock import patch

    push, _, _, coordinator, snap, _ = push_setup
    device_id = snap.device["iot_id"]
    with (
        patch(
            "custom_components.neakasa_litterbox.push.time.time",
            side_effect=[1000.0, 1098.0],
        ),
        patch.object(push._leveling_store, "async_save", new_callable=AsyncMock),
        patch.object(push._duration_store, "async_save", new_callable=AsyncMock),
    ):
        coordinator.leveling_state_callback(
            device_id, OperatingState.IDLE, OperatingState.LEVELING
        )
        from dataclasses import replace

        leveling_snapshot = replace(
            snap, status=replace(snap.status, operating_state=OperatingState.LEVELING)
        )
        coordinator.data = NeakasaPayload(devices={device_id: leveling_snapshot})
        push._handle_change(
            StatusUpdate(
                device_name=snap.device["device_name"],
                changes={"operating_state": OperatingState.IDLE},
            )
        )
        await hass.async_block_till_done()

    assert coordinator.leveling_events[device_id] == [1098]
    assert coordinator.leveling_durations[device_id][1098] == 98


async def test_mqtt_leveling_then_poll_idle_records_completion(push_setup, hass):
    from unittest.mock import patch

    push, _, _, coordinator, snap, _ = push_setup
    device_id = snap.device["iot_id"]
    with (
        patch(
            "custom_components.neakasa_litterbox.push.time.time",
            side_effect=[1000.0, 1098.0],
        ),
        patch.object(push._leveling_store, "async_save", new_callable=AsyncMock),
        patch.object(push._duration_store, "async_save", new_callable=AsyncMock),
    ):
        push._handle_change(
            StatusUpdate(
                device_name=snap.device["device_name"],
                changes={"operating_state": OperatingState.LEVELING},
            )
        )
        coordinator.leveling_state_callback(
            device_id, OperatingState.LEVELING, OperatingState.IDLE
        )
        await hass.async_block_till_done()

    assert coordinator.leveling_events[device_id] == [1098]
    assert coordinator.leveling_durations[device_id][1098] == 98
