"""Coordinator payload shapes aggregated from the Neakasa cloud."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping

    from neakasa_litterbox_sdk import Cat, DeviceStatus


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
    last_clean_at: int | None = None
    cat_stats: Mapping[int, NeakasaCatStats] = field(default_factory=dict)


@dataclass(frozen=True)
class NeakasaPayload:
    """Aggregated payload exposed by the coordinator (keyed by iot_id)."""

    devices: Mapping[str, NeakasaDeviceSnapshot]
