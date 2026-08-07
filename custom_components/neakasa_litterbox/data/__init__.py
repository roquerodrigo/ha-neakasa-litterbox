"""Typed data shapes for neakasa_litterbox."""

from .config import NeakasaConfigData, NeakasaOptionsData
from .diagnostics import NeakasaDiagnosticsEntry, NeakasaDiagnosticsPayload
from .json_types import JsonObject, JsonPrimitive, JsonValue
from .payload import (
    NeakasaCatStats,
    NeakasaDeviceInfo,
    NeakasaDeviceSnapshot,
    NeakasaPayload,
)
from .runtime import NeakasaConfigEntry, NeakasaData

__all__ = [
    "JsonObject",
    "JsonPrimitive",
    "JsonValue",
    "NeakasaCatStats",
    "NeakasaConfigData",
    "NeakasaConfigEntry",
    "NeakasaData",
    "NeakasaDeviceInfo",
    "NeakasaDeviceSnapshot",
    "NeakasaDiagnosticsEntry",
    "NeakasaDiagnosticsPayload",
    "NeakasaOptionsData",
    "NeakasaPayload",
]
