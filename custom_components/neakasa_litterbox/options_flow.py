"""Options flow for neakasa_litterbox."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.config_entries import ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers import selector

from .const import (
    CONF_STATISTICS_LOOKBACK_DAYS,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DEFAULT_STATISTICS_LOOKBACK_DAYS,
    MAX_STATISTICS_LOOKBACK_DAYS,
    MIN_SCAN_INTERVAL_SECONDS,
    MIN_STATISTICS_LOOKBACK_DAYS,
)

if TYPE_CHECKING:
    from .data import NeakasaOptionsData


class NeakasaOptionsFlow(OptionsFlow):
    """Options flow for Neakasa Litterbox."""

    async def async_step_init(
        self,
        user_input: NeakasaOptionsData | None = None,
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=dict(user_input))

        current_scan: int = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            DEFAULT_SCAN_INTERVAL_SECONDS,
        )
        current_lookback: int = self.config_entry.options.get(
            CONF_STATISTICS_LOOKBACK_DAYS,
            DEFAULT_STATISTICS_LOOKBACK_DAYS,
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current_scan,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL_SECONDS,
                            step=10,
                            unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        ),
                    ),
                    vol.Optional(
                        CONF_STATISTICS_LOOKBACK_DAYS,
                        default=current_lookback,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_STATISTICS_LOOKBACK_DAYS,
                            max=MAX_STATISTICS_LOOKBACK_DAYS,
                            step=1,
                            unit_of_measurement="d",
                            mode=selector.NumberSelectorMode.BOX,
                        ),
                    ),
                },
            ),
        )
