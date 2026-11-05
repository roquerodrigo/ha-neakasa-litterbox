from __future__ import annotations

from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.number import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID, ATTR_UNIT_OF_MEASUREMENT, UnitOfMass
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.neakasa_litterbox.data import (
    NeakasaDeviceSnapshot,
    NeakasaPayload,
)
from custom_components.neakasa_litterbox.exceptions import NeakasaApiClientError
from custom_components.neakasa_litterbox.number.calibrate_sand import (
    NeakasaCalibrateSandNumber,
)
from custom_components.neakasa_litterbox.number.cat_profile_weight import (
    NeakasaCatProfileWeightNumber,
)

_PROFILE_WEIGHT_UNIQUE_ID = "iot-id-1_cat_42_profile_weight"


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


async def test_setup_creates_device_and_cat_numbers(hass, setup_integration):
    assert len(hass.states.async_all("number")) == 2


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


def _profile_weight_entity_id(hass) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        "number", "neakasa_litterbox", _PROFILE_WEIGHT_UNIQUE_ID
    )
    assert entity_id is not None
    return entity_id


async def _set_value(hass, entity_id: str, value: float) -> None:
    await hass.services.async_call(
        "number",
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
        blocking=True,
    )


@pytest.fixture
def mock_set_cat_weight(mock_api_client) -> AsyncMock:
    mock_api_client.async_set_cat_weight = AsyncMock(return_value=None)
    return mock_api_client.async_set_cat_weight


async def test_profile_weight_reports_the_profile(hass, setup_integration):
    state = hass.states.get(_profile_weight_entity_id(hass))
    assert state is not None
    assert float(state.state) == 4.2
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfMass.KILOGRAMS


@pytest.mark.parametrize(
    ("profile_unit", "expected"),
    [("lb", UnitOfMass.POUNDS), ("", UnitOfMass.KILOGRAMS)],
)
async def test_profile_weight_follows_the_profile_unit(
    hass,
    mock_api_client,
    enable_custom_integrations,
    sample_cat,
    profile_unit,
    expected,
):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.neakasa_litterbox.const import DOMAIN

    mock_api_client.async_list_cats.return_value = [
        replace(sample_cat, unit=profile_unit)
    ]
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "u@x", "password": "p", "region": "us"},
        unique_id="ux",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(_profile_weight_entity_id(hass))
    assert state is not None
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == expected


async def test_profile_weight_is_unknown_without_a_saved_weight(
    hass, mock_api_client, sample_cat, setup_integration
):
    mock_api_client.async_list_cats.return_value = [replace(sample_cat, weight=0.0)]
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(_profile_weight_entity_id(hass))
    assert state is not None
    assert state.state == "unknown"


async def test_profile_weight_saves_to_the_profile(
    hass, mock_set_cat_weight, setup_integration
):
    await _set_value(hass, _profile_weight_entity_id(hass), 4.5)

    mock_set_cat_weight.assert_awaited_once()
    assert mock_set_cat_weight.await_args.args == ("dn-1", 42, 4.5)
    assert mock_set_cat_weight.await_args.kwargs["unit"] == "kg"


async def test_profile_weight_saves_in_the_profile_unit_when_shown_in_another(
    hass, mock_set_cat_weight, setup_integration
):
    entity_id = _profile_weight_entity_id(hass)
    er.async_get(hass).async_update_entity_options(
        entity_id, "number", {"unit_of_measurement": UnitOfMass.POUNDS}
    )
    await hass.async_block_till_done()

    await _set_value(hass, entity_id, 10)

    assert mock_set_cat_weight.await_args.args == ("dn-1", 42, 4.54)
    assert mock_set_cat_weight.await_args.kwargs["unit"] == "kg"


async def test_profile_weight_reports_a_cloud_failure(
    hass, mock_set_cat_weight, setup_integration
):
    mock_set_cat_weight.side_effect = NeakasaApiClientError("rejected")

    with pytest.raises(HomeAssistantError) as raised:
        await _set_value(hass, _profile_weight_entity_id(hass), 4.5)
    assert raised.value.translation_key == "set_cat_weight_failed"


async def test_profile_weight_no_op_without_the_cat(sample_device):
    coord = MagicMock()
    coord.data = NeakasaPayload(devices={})
    coord.last_update_success = True
    coord.async_request_refresh = AsyncMock()
    coord.config_entry.runtime_data.client = MagicMock()
    number = NeakasaCatProfileWeightNumber(coord, sample_device.iot_id, 42)
    await number.async_set_native_value(4.5)
    coord.async_request_refresh.assert_not_awaited()
    assert number.native_unit_of_measurement == UnitOfMass.KILOGRAMS
