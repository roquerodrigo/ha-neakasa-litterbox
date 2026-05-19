from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from custom_components.neakasa_litterbox.button.clean_now import NeakasaCleanNowButton
from custom_components.neakasa_litterbox.button.level_now import NeakasaLevelNowButton
from custom_components.neakasa_litterbox.data import (
    NeakasaDeviceSnapshot,
    NeakasaPayload,
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


async def test_setup_creates_two_buttons(hass, setup_integration):
    assert len(hass.states.async_all("button")) == 2


async def test_clean_now_press(sample_device, sample_status, sample_cat):
    snap = _snapshot(sample_device, sample_status, sample_cat)
    client = MagicMock()
    client.async_start_clean = AsyncMock()
    coord = _coord(snap, client)
    btn = NeakasaCleanNowButton(coord, sample_device.iot_id)
    assert btn.unique_id == f"{sample_device.iot_id}_clean_now"
    await btn.async_press()
    client.async_start_clean.assert_awaited_with(sample_device.device_name)
    coord.async_request_refresh.assert_awaited_once()


async def test_level_now_press(sample_device, sample_status, sample_cat):
    snap = _snapshot(sample_device, sample_status, sample_cat)
    client = MagicMock()
    client.async_start_level = AsyncMock()
    coord = _coord(snap, client)
    btn = NeakasaLevelNowButton(coord, sample_device.iot_id)
    assert btn.unique_id == f"{sample_device.iot_id}_level_now"
    await btn.async_press()
    client.async_start_level.assert_awaited_with(sample_device.device_name)


async def test_clean_now_no_op_without_snapshot(sample_device):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    coord.async_request_refresh = AsyncMock()
    coord.config_entry.runtime_data.client = MagicMock()
    btn = NeakasaCleanNowButton(coord, sample_device.iot_id)
    await btn.async_press()
    coord.async_request_refresh.assert_not_awaited()


async def test_level_now_no_op_without_snapshot(sample_device):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    coord.async_request_refresh = AsyncMock()
    coord.config_entry.runtime_data.client = MagicMock()
    btn = NeakasaLevelNowButton(coord, sample_device.iot_id)
    await btn.async_press()
    coord.async_request_refresh.assert_not_awaited()
