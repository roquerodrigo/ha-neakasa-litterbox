"""Runtime data stored on the config entry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from ..api import NeakasaApiClient
    from ..coordinator import NeakasaDataUpdateCoordinator
    from ..push import NeakasaPushClient


type NeakasaConfigEntry = ConfigEntry[NeakasaData]


@dataclass
class NeakasaData:
    """Data stored on entry.runtime_data for the Neakasa Litterbox integration."""

    client: NeakasaApiClient
    coordinator: NeakasaDataUpdateCoordinator
    integration: Integration
    push: NeakasaPushClient
