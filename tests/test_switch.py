from __future__ import annotations

import dataclasses
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.neakasa_litterbox.data import (
    NeakasaDeviceSnapshot,
    NeakasaPayload,
)
from custom_components.neakasa_litterbox.switch.auto_clean import (
    NeakasaAutoCleanSwitch,
)
from custom_components.neakasa_litterbox.switch.auto_level import (
    NeakasaAutoLevelSwitch,
)
from custom_components.neakasa_litterbox.switch.child_lock import (
    NeakasaChildLockSwitch,
)
from custom_components.neakasa_litterbox.switch.silent_mode import (
    NeakasaSilentModeSwitch,
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


async def test_setup_creates_four_switches(hass, setup_integration):
    assert len(hass.states.async_all("switch")) == 4


@pytest.mark.parametrize(
    ("entity_cls", "status_field", "method"),
    [
        (NeakasaAutoCleanSwitch, "cleaning_enabled", "async_set_auto_clean"),
        (NeakasaAutoLevelSwitch, "auto_level", "async_set_auto_level"),
        (NeakasaSilentModeSwitch, "silent_mode", "async_set_silent_mode"),
        (NeakasaChildLockSwitch, "child_lock", "async_set_child_lock"),
    ],
)
async def test_switch_reads_status_and_calls_client(
    sample_device, sample_status, sample_cat, entity_cls, status_field, method
):
    status = dataclasses.replace(sample_status, **{status_field: True})
    snap = _snapshot(sample_device, status, sample_cat)
    client = MagicMock()
    setattr(client, method, AsyncMock())
    coord = _coord(snap, client)
    s = entity_cls(coord, sample_device.iot_id)
    assert s.is_on is True

    await s.async_turn_off()
    getattr(client, method).assert_awaited_with(
        sample_device.device_name, enabled=False
    )
    # Optimistic patch: snapshot status reflects the new value immediately.
    assert (
        getattr(
            coord.async_set_updated_data.call_args.args[0]
            .devices[sample_device.iot_id]
            .status,
            status_field,
        )
        is False
    )
    await s.async_turn_on()
    getattr(client, method).assert_awaited_with(sample_device.device_name, enabled=True)
    assert (
        getattr(
            coord.async_set_updated_data.call_args.args[0]
            .devices[sample_device.iot_id]
            .status,
            status_field,
        )
        is True
    )
    coord.async_request_refresh.assert_not_awaited()


def test_switch_is_on_none_without_snapshot(sample_device):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    s = NeakasaAutoCleanSwitch(coord, sample_device.iot_id)
    assert s.is_on is None


async def test_switch_no_op_without_snapshot(sample_device):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    coord.async_request_refresh = AsyncMock()
    coord.config_entry.runtime_data.client = MagicMock()
    s = NeakasaAutoLevelSwitch(coord, sample_device.iot_id)
    await s.async_turn_on()
    coord.async_request_refresh.assert_not_awaited()


async def test_silent_mode_no_op_without_snapshot(sample_device):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    coord.async_request_refresh = AsyncMock()
    coord.config_entry.runtime_data.client = MagicMock()
    s = NeakasaSilentModeSwitch(coord, sample_device.iot_id)
    await s.async_turn_on()
    coord.async_request_refresh.assert_not_awaited()


async def test_child_lock_no_op_without_snapshot(sample_device):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    coord.async_request_refresh = AsyncMock()
    coord.config_entry.runtime_data.client = MagicMock()
    s = NeakasaChildLockSwitch(coord, sample_device.iot_id)
    await s.async_turn_on()
    coord.async_request_refresh.assert_not_awaited()


async def test_auto_clean_no_op_without_snapshot(sample_device):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    coord.async_request_refresh = AsyncMock()
    coord.config_entry.runtime_data.client = MagicMock()
    s = NeakasaAutoCleanSwitch(coord, sample_device.iot_id)
    await s.async_turn_on()
    coord.async_request_refresh.assert_not_awaited()
