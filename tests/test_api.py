from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from neakasa_litterbox_sdk import (
    ApiError,
    AuthenticationError,
    InvalidCredentialsError,
    NeakasaError,
    SessionExpiredError,
    TransportError,
)

from custom_components.neakasa_litterbox.api import NeakasaApiClient, _translate_errors
from custom_components.neakasa_litterbox.exceptions import (
    NeakasaApiClientAuthenticationError,
    NeakasaApiClientCommunicationError,
    NeakasaApiClientError,
)


def _client(sdk_mock=None) -> NeakasaApiClient:
    with patch(
        "custom_components.neakasa_litterbox.api.NeakasaClient",
        return_value=sdk_mock or MagicMock(),
    ):
        return NeakasaApiClient(username="u@x", password="p", region="us")


def test_translate_invalid_credentials_to_auth_error():
    with (
        pytest.raises(NeakasaApiClientAuthenticationError),
        _translate_errors(),
    ):
        raise InvalidCredentialsError("nope", code=401)


def test_translate_session_expired_to_auth_error():
    with (
        pytest.raises(NeakasaApiClientAuthenticationError),
        _translate_errors(),
    ):
        raise SessionExpiredError("expired", code=401)


def test_translate_auth_error_to_auth_error():
    with (
        pytest.raises(NeakasaApiClientAuthenticationError),
        _translate_errors(),
    ):
        raise AuthenticationError("bad", code=401)


def test_translate_transport_to_communication_error():
    with (
        pytest.raises(NeakasaApiClientCommunicationError),
        _translate_errors(),
    ):
        raise TransportError("network")


def test_translate_api_error_to_base_error():
    with pytest.raises(NeakasaApiClientError), _translate_errors():
        raise ApiError("api boom", code=500)


def test_translate_neakasa_error_to_base_error():
    with pytest.raises(NeakasaApiClientError), _translate_errors():
        raise NeakasaError("generic")


def test_translate_no_error_passes():
    with _translate_errors():
        pass


def test_unknown_region_raises_api_error():
    with pytest.raises(NeakasaApiClientError, match="Unknown Neakasa region"):
        NeakasaApiClient(username="u@x", password="p", region="ZZ")


def test_constructor_uses_known_region():
    with patch("custom_components.neakasa_litterbox.api.NeakasaClient") as mock_sdk:
        client = NeakasaApiClient(username="u@x", password="p", region="eu")
    assert client.sdk is mock_sdk.return_value
    assert mock_sdk.call_args.kwargs["email"] == "u@x"
    assert mock_sdk.call_args.kwargs["region"].name == "EU"


async def test_async_login_calls_sdk():
    sdk = MagicMock()
    sdk.login = AsyncMock()
    client = _client(sdk)
    await client.async_login()
    sdk.login.assert_awaited_once()


async def test_async_login_translates_auth_error():
    sdk = MagicMock()
    sdk.login = AsyncMock(side_effect=InvalidCredentialsError("nope", code=401))
    client = _client(sdk)
    with pytest.raises(NeakasaApiClientAuthenticationError):
        await client.async_login()


async def test_async_close_swallows_sdk_error():
    sdk = MagicMock()
    sdk.close = AsyncMock(side_effect=NeakasaError("ugly"))
    client = _client(sdk)
    await client.async_close()
    sdk.close.assert_awaited_once()


async def test_list_devices_delegates(sample_device):
    sdk = MagicMock()
    sdk.list_devices = AsyncMock(return_value=[sample_device])
    client = _client(sdk)
    assert await client.async_list_devices() == [sample_device]


async def test_get_status_delegates(sample_status):
    sdk = MagicMock()
    sdk.get_status = AsyncMock(return_value=sample_status)
    client = _client(sdk)
    assert await client.async_get_status("dn-1") is sample_status


async def test_list_cats_delegates(sample_cat):
    sdk = MagicMock()
    sdk.list_cats = AsyncMock(return_value=[sample_cat])
    client = _client(sdk)
    assert await client.async_list_cats("dn-1") == [sample_cat]


async def test_get_toilet_records_delegates(sample_record):
    sdk = MagicMock()
    sdk.get_toilet_records = AsyncMock(return_value=[sample_record])
    client = _client(sdk)
    assert await client.async_get_toilet_records("dn-1", 0, 1) == [sample_record]


async def test_get_toilet_statistics_delegates():
    sdk = MagicMock()
    sdk.get_toilet_statistics = AsyncMock(return_value=[])
    client = _client(sdk)
    assert await client.async_get_toilet_statistics("dn-1", 0, 1) == []
    sdk.get_toilet_statistics.assert_awaited_once_with("dn-1", 0, 1, zone_seconds=0)


@pytest.mark.parametrize(
    ("attr", "method"),
    [
        ("start_clean", "async_start_clean"),
        ("stop_clean", "async_stop_clean"),
        ("start_level", "async_start_level"),
        ("stop_level", "async_stop_level"),
    ],
)
async def test_command_methods_delegate(attr, method):
    sdk = MagicMock()
    setattr(sdk, attr, AsyncMock())
    client = _client(sdk)
    await getattr(client, method)("dn-1")
    getattr(sdk, attr).assert_awaited_once_with("dn-1")


async def test_calibrate_sand_delegates():
    sdk = MagicMock()
    sdk.calibrate_sand = AsyncMock()
    client = _client(sdk)
    await client.async_calibrate_sand("dn-1", 55)
    sdk.calibrate_sand.assert_awaited_once_with("dn-1", 55)


@pytest.mark.parametrize(
    ("attr", "method"),
    [
        ("set_auto_clean", "async_set_auto_clean"),
        ("set_auto_level", "async_set_auto_level"),
        ("set_silent_mode", "async_set_silent_mode"),
        ("set_child_lock", "async_set_child_lock"),
    ],
)
async def test_set_flag_methods_delegate(attr, method):
    sdk = MagicMock()
    setattr(sdk, attr, AsyncMock())
    client = _client(sdk)
    await getattr(client, method)("dn-1", enabled=True)
    getattr(sdk, attr).assert_awaited_once_with("dn-1", True)


def test_watch_status_returns_sdk_stream():
    sdk = MagicMock()
    sentinel = MagicMock()
    sdk.watch_status = MagicMock(return_value=sentinel)
    client = _client(sdk)
    assert client.watch_status() is sentinel
