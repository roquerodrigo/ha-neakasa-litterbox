from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.neakasa_litterbox.const import DOMAIN
from custom_components.neakasa_litterbox.coordinator import (
    NeakasaDataUpdateCoordinator,
    _build_snapshot,
    scan_interval_from_options,
)
from custom_components.neakasa_litterbox.data import NeakasaPayload
from custom_components.neakasa_litterbox.exceptions import (
    NeakasaApiClientAuthenticationError,
    NeakasaApiClientDeviceBusyError,
    NeakasaApiClientError,
)


def _make_coordinator(hass, client):
    coord = NeakasaDataUpdateCoordinator(
        hass=hass, scan_interval=timedelta(seconds=300)
    )
    runtime_data = type("D", (), {"client": client})()
    entry = type(
        "E", (), {"entry_id": "eid", "runtime_data": runtime_data, "options": {}}
    )()
    coord.config_entry = entry
    return coord


def test_init_sets_domain_name(hass):
    coord = NeakasaDataUpdateCoordinator(
        hass=hass, scan_interval=timedelta(seconds=300)
    )
    assert coord.name == DOMAIN


def test_init_sets_update_interval(hass):
    coord = NeakasaDataUpdateCoordinator(hass=hass, scan_interval=timedelta(seconds=42))
    assert coord.update_interval == timedelta(seconds=42)


def test_scan_interval_from_options_default():
    assert scan_interval_from_options({}) == 600


def test_scan_interval_from_options_picks_value():
    assert scan_interval_from_options({"scan_interval": 90}) == 90


async def test_update_data_returns_payload(
    hass, sample_device, sample_status, sample_cat, sample_record
):
    client = MagicMock()
    client.async_list_devices = AsyncMock(return_value=[sample_device])
    client.async_get_status = AsyncMock(return_value=sample_status)
    client.async_list_cats = AsyncMock(return_value=[sample_cat])
    client.async_get_toilet_records = AsyncMock(return_value=[sample_record])

    coord = _make_coordinator(hass, client)
    payload = await coord._async_update_data()
    assert list(payload.devices.keys()) == [sample_device.iot_id]
    snap = payload.devices[sample_device.iot_id]
    assert snap.status is sample_status
    assert snap.cats == (sample_cat,)


async def test_update_data_raises_update_failed_on_api_error(hass):
    client = MagicMock()
    client.async_list_devices = AsyncMock(side_effect=NeakasaApiClientError("down"))
    coord = _make_coordinator(hass, client)
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()


async def test_update_data_keeps_last_payload_when_device_busy(
    hass, sample_device, sample_cat, sample_record
):
    # Mid-cycle the cloud rejects the status readback (29003); the
    # coordinator must hand back the previous payload, not fail.
    client = MagicMock()
    client.async_list_devices = AsyncMock(return_value=[sample_device])
    client.async_get_status = AsyncMock(
        side_effect=NeakasaApiClientDeviceBusyError("29003")
    )
    client.async_list_cats = AsyncMock(return_value=[sample_cat])
    client.async_get_toilet_records = AsyncMock(return_value=[sample_record])
    coord = _make_coordinator(hass, client)
    previous = NeakasaPayload(devices={})
    coord.data = previous
    assert await coord._async_update_data() is previous


async def test_update_data_busy_without_prior_data_raises(hass, sample_device):
    client = MagicMock()
    client.async_list_devices = AsyncMock(return_value=[sample_device])
    client.async_get_status = AsyncMock(
        side_effect=NeakasaApiClientDeviceBusyError("29003")
    )
    client.async_list_cats = AsyncMock(return_value=[])
    client.async_get_toilet_records = AsyncMock(return_value=[])
    coord = _make_coordinator(hass, client)
    coord.data = None
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()


async def test_update_data_raises_auth_failed_on_auth_error(hass):
    client = MagicMock()
    client.async_list_devices = AsyncMock(
        side_effect=NeakasaApiClientAuthenticationError("nope")
    )
    coord = _make_coordinator(hass, client)
    with pytest.raises(ConfigEntryAuthFailed):
        await coord._async_update_data()


def test_build_snapshot_counts_today_visits(
    sample_device, sample_status, sample_cat, sample_record
):
    from neakasa_litterbox_sdk import RecordType, ToiletRecord

    today_record = ToiletRecord(
        record_id=99,
        record_type=RecordType.CAT_VISIT,
        cat_id=sample_cat.id,
        start_time=int(__import__("time").time()),
        end_time=int(__import__("time").time()),
        weight=3.5,
        unit="kg",
        way=0,
    )
    clean_record = ToiletRecord(
        record_id=100,
        record_type=RecordType.CLEAN_CYCLE,
        cat_id=0,
        start_time=int(__import__("time").time()),
        end_time=int(__import__("time").time()),
        weight=0.0,
        unit="kg",
        way=0,
    )
    snap = _build_snapshot(
        sample_device,
        sample_status,
        [sample_cat],
        [sample_record, today_record, clean_record],
    )
    assert snap.visits_today == 1
    assert snap.last_visit_at == max(sample_record.start_time, today_record.start_time)
    assert snap.cat_stats[sample_cat.id]["visits_today"] == 1


def test_build_snapshot_handles_no_records(sample_device, sample_status, sample_cat):
    snap = _build_snapshot(sample_device, sample_status, [sample_cat], [])
    assert snap.visits_today == 0
    assert snap.last_visit_at is None
    assert snap.cat_stats[sample_cat.id]["last_visit_at"] is None
