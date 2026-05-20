from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.neakasa_litterbox.const import (
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)
from custom_components.neakasa_litterbox.exceptions import (
    NeakasaApiClientAuthenticationError,
    NeakasaApiClientCommunicationError,
)


async def test_setup_entry_loads_successfully(setup_integration):
    assert setup_integration.state == ConfigEntryState.LOADED


async def test_setup_entry_creates_device_entities(hass, setup_integration):
    # 3 device sensors + 3 cat sensors = 6
    assert len(hass.states.async_all("sensor")) == 6


async def test_setup_entry_creates_binary_sensor_entities(hass, setup_integration):
    assert len(hass.states.async_all("binary_sensor")) == 2


async def test_setup_entry_creates_switch_entities(hass, setup_integration):
    assert len(hass.states.async_all("switch")) == 4


async def test_setup_entry_creates_button_entities(hass, setup_integration):
    assert len(hass.states.async_all("button")) == 2


async def test_setup_entry_creates_number_entities(hass, setup_integration):
    assert len(hass.states.async_all("number")) == 1


async def test_unload_entry_succeeds(hass, setup_integration):
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    assert setup_integration.state == ConfigEntryState.NOT_LOADED


async def test_unload_entry_makes_entities_unavailable(hass, setup_integration):
    await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()
    for state in hass.states.async_all("sensor"):
        assert state.state == "unavailable"


async def test_reload_entry_restores_loaded_state(hass, setup_integration):
    await hass.config_entries.async_reload(setup_integration.entry_id)
    await hass.async_block_till_done()
    assert setup_integration.state == ConfigEntryState.LOADED


async def test_runtime_data_populated(setup_integration):
    assert setup_integration.runtime_data.client is not None
    assert setup_integration.runtime_data.coordinator is not None
    assert setup_integration.runtime_data.integration is not None
    assert setup_integration.runtime_data.push is not None


async def test_scan_interval_defaults_to_const(setup_integration):
    assert setup_integration.runtime_data.coordinator.update_interval == timedelta(
        seconds=DEFAULT_SCAN_INTERVAL_SECONDS
    )


async def test_scan_interval_picks_up_options(
    hass, mock_api_client, enable_custom_integrations
):
    from homeassistant.const import CONF_SCAN_INTERVAL

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "u@x", "password": "p", "region": "us"},
        options={CONF_SCAN_INTERVAL: 90},
        unique_id="ux",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.coordinator.update_interval == timedelta(seconds=90)


async def test_setup_entry_translates_auth_error(hass, enable_custom_integrations):
    with patch("custom_components.neakasa_litterbox.NeakasaApiClient") as mock_class:
        mock_class.return_value.async_login = AsyncMock(
            side_effect=NeakasaApiClientAuthenticationError("bad")
        )
        mock_class.return_value.async_close = AsyncMock(return_value=None)
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={"username": "u@x", "password": "p", "region": "us"},
            unique_id="ux",
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.SETUP_ERROR


async def test_setup_entry_translates_communication_error(
    hass, enable_custom_integrations
):
    with patch("custom_components.neakasa_litterbox.NeakasaApiClient") as mock_class:
        mock_class.return_value.async_login = AsyncMock(
            side_effect=NeakasaApiClientCommunicationError("down")
        )
        mock_class.return_value.async_close = AsyncMock(return_value=None)
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={"username": "u@x", "password": "p", "region": "us"},
            unique_id="ux2",
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.SETUP_RETRY
