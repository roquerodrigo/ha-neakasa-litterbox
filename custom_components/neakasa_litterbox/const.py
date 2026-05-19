"""Constants for neakasa_litterbox."""

from __future__ import annotations

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "neakasa_litterbox"
MANUFACTURER = "Neakasa"
ATTRIBUTION = "Data provided by the Neakasa cloud"

DEFAULT_SCAN_INTERVAL_SECONDS = 600
MIN_SCAN_INTERVAL_SECONDS = 60

DEFAULT_STATISTICS_LOOKBACK_DAYS = 7
MIN_STATISTICS_LOOKBACK_DAYS = 1
MAX_STATISTICS_LOOKBACK_DAYS = 30

CONF_REGION = "region"
CONF_STATISTICS_LOOKBACK_DAYS = "statistics_lookback_days"

REGION_US = "US"
REGION_EU = "EU"
REGION_AP = "AP"
REGIONS: tuple[str, ...] = (REGION_US, REGION_EU, REGION_AP)
DEFAULT_REGION = REGION_US
