"""Shapes of the data and options persisted on the config entry."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class NeakasaConfigData(TypedDict):
    """Shape of the credentials persisted on the config entry."""

    username: str
    password: str
    region: str


class NeakasaOptionsData(TypedDict, total=False):
    """Shape of the options writable by the options flow."""

    scan_interval: NotRequired[int]
    statistics_lookback_days: NotRequired[int]
