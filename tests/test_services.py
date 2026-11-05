from __future__ import annotations

from unittest.mock import ANY, AsyncMock

import probatio
import pytest
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr

from custom_components.neakasa_litterbox.const import DOMAIN
from custom_components.neakasa_litterbox.exceptions import (
    NeakasaApiClientCommunicationError,
)
from custom_components.neakasa_litterbox.services import SERVICE_SET_CAT_WEIGHT


def _cat_device_id(hass, entry) -> str:
    device = dr.async_get(hass).async_get_child_device_by_identifier(
        (DOMAIN, "iot-id-1-cat-42"), entry.entry_id
    )
    assert device is not None
    return device.id


def _litter_box_device_id(hass, entry) -> str:
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "iot-id-1"), entry.entry_id
    )
    assert device is not None
    return device.id


async def _set_cat_weight(hass, device_id: str, weight: float, unit: str) -> None:
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_CAT_WEIGHT,
        {"device_id": device_id, "weight": weight, "unit": unit},
        blocking=True,
    )


@pytest.fixture
def mock_set_cat_weight(mock_api_client) -> AsyncMock:
    mock_api_client.async_set_cat_weight = AsyncMock(return_value=None)
    return mock_api_client.async_set_cat_weight


async def test_service_is_registered(hass, setup_integration):
    assert hass.services.has_service(DOMAIN, SERVICE_SET_CAT_WEIGHT)


async def test_saves_the_weight_to_the_cat_profile(
    hass, local_day, mock_set_cat_weight, setup_integration
):
    coordinator = setup_integration.runtime_data.coordinator
    coordinator.async_request_refresh = AsyncMock()

    await _set_cat_weight(hass, _cat_device_id(hass, setup_integration), 4.8, "kg")

    mock_set_cat_weight.assert_awaited_once_with(
        "dn-1", 42, 4.8, unit="kg", zone_seconds=3600
    )
    coordinator.async_request_refresh.assert_awaited_once()


async def test_accepts_pounds(hass, mock_set_cat_weight, setup_integration):
    await _set_cat_weight(hass, _cat_device_id(hass, setup_integration), 10.6, "lb")

    mock_set_cat_weight.assert_awaited_once_with(
        "dn-1", 42, 10.6, unit="lb", zone_seconds=ANY
    )


async def test_rejects_a_litter_box_device(
    hass, mock_set_cat_weight, setup_integration
):
    with pytest.raises(ServiceValidationError) as raised:
        await _set_cat_weight(
            hass, _litter_box_device_id(hass, setup_integration), 4.8, "kg"
        )
    assert raised.value.translation_key == "not_a_cat"
    assert raised.value.translation_placeholders == {"device_name": "Neakasa M1"}
    mock_set_cat_weight.assert_not_awaited()


async def test_rejects_a_cat_the_cloud_no_longer_reports(
    hass, mock_api_client, mock_set_cat_weight, setup_integration
):
    device_id = _cat_device_id(hass, setup_integration)
    mock_api_client.async_list_cats.return_value = []
    await setup_integration.runtime_data.coordinator.async_refresh()

    with pytest.raises(ServiceValidationError) as raised:
        await _set_cat_weight(hass, device_id, 4.8, "kg")
    assert raised.value.translation_key == "not_a_cat"
    mock_set_cat_weight.assert_not_awaited()


async def test_reports_a_cloud_failure(hass, mock_set_cat_weight, setup_integration):
    mock_set_cat_weight.side_effect = NeakasaApiClientCommunicationError("down")

    with pytest.raises(HomeAssistantError) as raised:
        await _set_cat_weight(hass, _cat_device_id(hass, setup_integration), 4.8, "kg")
    assert raised.value.translation_key == "set_cat_weight_failed"
    assert raised.value.translation_placeholders == {
        "cat_name": "Whiskers",
        "error": "down",
    }


@pytest.mark.parametrize(("weight", "unit"), [(0, "kg"), (-1.5, "kg"), (4.8, "g")])
async def test_rejects_invalid_input(
    hass, mock_set_cat_weight, setup_integration, weight, unit
):
    with pytest.raises(probatio.Invalid):
        await _set_cat_weight(
            hass, _cat_device_id(hass, setup_integration), weight, unit
        )
    mock_set_cat_weight.assert_not_awaited()
