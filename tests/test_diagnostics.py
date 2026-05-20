from __future__ import annotations

from custom_components.neakasa_litterbox.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_redacts_username(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert diag["entry"]["data"]["username"] == "**REDACTED**"


async def test_diagnostics_redacts_password(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert diag["entry"]["data"]["password"] == "**REDACTED**"


async def test_diagnostics_keeps_region(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert diag["entry"]["data"]["region"] == "us"


async def test_diagnostics_includes_entry_metadata(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert diag["entry"]["domain"] == "neakasa_litterbox"
    assert diag["entry"]["version"] == 1


async def test_diagnostics_includes_devices(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert len(diag["devices"]) == 1
    assert diag["devices"][0]["iot_id"] == "iot-id-1"


async def test_diagnostics_options_present(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert isinstance(diag["entry"]["options"], dict)
