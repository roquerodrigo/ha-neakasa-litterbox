from __future__ import annotations

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResultType

from custom_components.neakasa_litterbox.const import (
    CONF_STATISTICS_LOOKBACK_DAYS,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DEFAULT_STATISTICS_LOOKBACK_DAYS,
)


async def test_options_flow_shows_form_with_defaults(hass, setup_integration):
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    assert result["type"] == FlowResultType.FORM
    schema = result["data_schema"].schema
    scan_key = next(k for k in schema if getattr(k, "schema", k) == CONF_SCAN_INTERVAL)
    look_key = next(
        k for k in schema if getattr(k, "schema", k) == CONF_STATISTICS_LOOKBACK_DAYS
    )
    assert scan_key.default() == DEFAULT_SCAN_INTERVAL_SECONDS
    assert look_key.default() == DEFAULT_STATISTICS_LOOKBACK_DAYS


async def test_options_flow_persists_values(hass, setup_integration):
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 120, CONF_STATISTICS_LOOKBACK_DAYS: 14},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert setup_integration.options[CONF_SCAN_INTERVAL] == 120
    assert setup_integration.options[CONF_STATISTICS_LOOKBACK_DAYS] == 14


async def test_options_flow_uses_existing_as_default(hass, setup_integration):
    hass.config_entries.async_update_entry(
        setup_integration,
        options={CONF_SCAN_INTERVAL: 180, CONF_STATISTICS_LOOKBACK_DAYS: 30},
    )
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    schema = result["data_schema"].schema
    scan_key = next(k for k in schema if getattr(k, "schema", k) == CONF_SCAN_INTERVAL)
    assert scan_key.default() == 180
