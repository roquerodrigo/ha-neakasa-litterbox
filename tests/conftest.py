from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from neakasa_litterbox_sdk import (
    Cat,
    CatGender,
    Device,
    DeviceRole,
    DeviceStatus,
    OperatingState,
    RecordType,
    ToiletRecord,
)

if TYPE_CHECKING:
    from collections.abc import Generator


pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture
def sample_device() -> Device:
    return Device(
        iot_id="iot-id-1",
        product_key="pk",
        product_name="Neakasa M1",
        device_name="dn-1",
        category_key="ck",
        category_name="Litter Box",
        net_type="wifi",
        role=DeviceRole.OWNER,
        status=1,
        bind_time=0,
    )


@pytest.fixture
def sample_status() -> DeviceStatus:
    return DeviceStatus(
        sand_percent=60,
        cat_present=False,
        cat_stay_seconds=0,
        needs_cleaning=False,
        bucket_full=False,
        operating_state=OperatingState.IDLE,
        last_sand_added="2026-05-19 10:00:00",
        cleaning_enabled=True,
        auto_level=True,
        silent_mode=False,
        child_lock=False,
        young_cat_mode=False,
        last_action="idle",
        wifi_name="home",
        wifi_rssi=-50,
        ip_address="10.0.0.1",
        mac_address="aa:bb:cc:dd:ee:ff",
        firmware_version="1.2.3",
        hardware_version="1.0",
        updated_at=1700000000,
    )


@pytest.fixture
def sample_cat() -> Cat:
    return Cat(
        id=42,
        name="Whiskers",
        weight=4.2,
        unit="kg",
        avatar="",
        birthday="2020-01-01",
        variety=0,
        gender=CatGender.UNKNOWN,
        sterilization=0,
        enabled=1,
        path="",
    )


@pytest.fixture
def sample_record() -> ToiletRecord:
    return ToiletRecord(
        record_id=1,
        record_type=RecordType.CAT_VISIT,
        cat_id=42,
        start_time=1_700_000_500,
        end_time=1_700_000_600,
        weight=4.1,
        unit="kg",
        way=0,
    )


@pytest.fixture
def enable_custom_integrations(hass) -> None:
    from homeassistant.loader import DATA_CUSTOM_COMPONENTS

    hass.data.pop(DATA_CUSTOM_COMPONENTS, None)


@pytest.fixture
def mock_api_client(
    sample_device: Device,
    sample_status: DeviceStatus,
    sample_cat: Cat,
    sample_record: ToiletRecord,
) -> Generator:
    stream = MagicMock()
    stream.start = AsyncMock()
    stream.stop = AsyncMock()

    with (
        patch(
            "custom_components.neakasa_litterbox.NeakasaApiClient"
        ) as mock_setup_class,
        patch(
            "custom_components.neakasa_litterbox.config_flow.NeakasaApiClient"
        ) as mock_flow_class,
    ):
        instance = mock_setup_class.return_value
        instance.async_login = AsyncMock(return_value=None)
        instance.async_close = AsyncMock(return_value=None)
        instance.async_list_devices = AsyncMock(return_value=[sample_device])
        instance.async_get_status = AsyncMock(return_value=sample_status)
        instance.async_list_cats = AsyncMock(return_value=[sample_cat])
        instance.async_get_toilet_records = AsyncMock(return_value=[sample_record])
        instance.async_set_auto_clean = AsyncMock(return_value=None)
        instance.async_set_auto_level = AsyncMock(return_value=None)
        instance.async_set_silent_mode = AsyncMock(return_value=None)
        instance.async_set_child_lock = AsyncMock(return_value=None)
        instance.async_start_clean = AsyncMock(return_value=None)
        instance.async_start_level = AsyncMock(return_value=None)
        instance.async_calibrate_sand = AsyncMock(return_value=None)
        instance.watch_status = MagicMock(return_value=stream)
        mock_flow_class.return_value = instance
        yield instance


@pytest.fixture
async def setup_integration(hass, mock_api_client, enable_custom_integrations):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.neakasa_litterbox.const import DOMAIN

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "user@example.com",
            "password": "pass",
            "region": "us",
        },
        unique_id="user-example-com",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
