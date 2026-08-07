"""Shapes of the diagnostics dump returned to Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .payload import NeakasaDeviceInfo


class NeakasaDiagnosticsEntry(TypedDict):
    """Entry section of the diagnostics dump."""

    title: str
    version: int
    domain: str
    data: Mapping[str, str]
    options: Mapping[str, str | int]


class NeakasaDiagnosticsPayload(TypedDict):
    """Top-level shape returned by async_get_config_entry_diagnostics."""

    entry: NeakasaDiagnosticsEntry
    devices: list[NeakasaDeviceInfo]
