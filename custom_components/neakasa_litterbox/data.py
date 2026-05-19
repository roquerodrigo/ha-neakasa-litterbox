"""Custom types for neakasa_litterbox."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NotRequired, TypedDict

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration
    from neakasa_litterbox_sdk import Cat, DeviceStatus

    from .api import NeakasaApiClient
    from .coordinator import NeakasaDataUpdateCoordinator
    from .push import NeakasaPushClient


type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | list[JsonValue] | Mapping[str, JsonValue]
type JsonObject = Mapping[str, JsonValue]


class NeakasaConfigData(TypedDict):
    """Shape of the credentials persisted on the config entry."""

    username: str
    password: str
    region: str


class NeakasaOptionsData(TypedDict, total=False):
    """Shape of the options writable by the options flow."""

    scan_interval: NotRequired[int]
    statistics_lookback_days: NotRequired[int]


class NeakasaDiagnosticsEntry(TypedDict):
    """Entry section of the diagnostics dump."""

    title: str
    version: int
    domain: str
    data: Mapping[str, str]
    options: Mapping[str, str | int]


class NeakasaDeviceInfo(TypedDict):
    """Identity of a single litter box, surfaced into diagnostics."""

    iot_id: str
    device_name: str
    product_name: str
    firmware_version: str
    hardware_version: str


class NeakasaCatStats(TypedDict):
    """Per-cat aggregates derived from toilet records of the lookback window."""

    last_visit_at: int | None
    last_visit_weight: float | None
    visits_today: int


@dataclass(frozen=True)
class NeakasaDeviceSnapshot:
    """Per-device snapshot stored in coordinator data."""

    device: NeakasaDeviceInfo
    status: DeviceStatus
    cats: tuple[Cat, ...]
    visits_today: int
    last_visit_at: int | None
    cat_stats: Mapping[int, NeakasaCatStats] = field(default_factory=dict)


@dataclass(frozen=True)
class NeakasaPayload:
    """Aggregated payload exposed by the coordinator (keyed by iot_id)."""

    devices: Mapping[str, NeakasaDeviceSnapshot]


class NeakasaDiagnosticsPayload(TypedDict):
    """Top-level shape returned by async_get_config_entry_diagnostics."""

    entry: NeakasaDiagnosticsEntry
    devices: list[NeakasaDeviceInfo]


type NeakasaConfigEntry = ConfigEntry[NeakasaData]


@dataclass
class NeakasaData:
    """Data stored on entry.runtime_data for the Neakasa Litterbox integration."""

    client: NeakasaApiClient
    coordinator: NeakasaDataUpdateCoordinator
    integration: Integration
    push: NeakasaPushClient
