"""The weight saved in a cat's profile, which the litter box uses to tell cats apart."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Literal

from homeassistant.const import UnitOfMass
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .exceptions import NeakasaApiClientError

if TYPE_CHECKING:
    from neakasa_litterbox_sdk import Cat

    from .data import NeakasaConfigEntry, NeakasaDeviceSnapshot

type CatWeightUnit = Literal["kg", "lb"]

CAT_WEIGHT_UNITS: tuple[CatWeightUnit, ...] = ("kg", "lb")

_WEIGHT_UNIT_ALIASES = {
    "kg": UnitOfMass.KILOGRAMS,
    "lb": UnitOfMass.POUNDS,
    "lbs": UnitOfMass.POUNDS,
}


def normalize_weight_unit(unit: str | None) -> str | None:
    """Return the Home Assistant mass unit for a Neakasa unit string."""
    if not unit:
        return None
    return _WEIGHT_UNIT_ALIASES.get(unit.strip().casefold())


def cat_weight_unit(unit: str) -> CatWeightUnit:
    """Return the Neakasa unit for a Home Assistant mass unit."""
    return "lb" if unit == UnitOfMass.POUNDS else "kg"


def _utc_offset_seconds() -> int:
    """Return the offset of Home Assistant's time zone from UTC, in seconds."""
    return int((dt_util.now().utcoffset() or timedelta()).total_seconds())


async def async_save_cat_weight(
    entry: NeakasaConfigEntry,
    snapshot: NeakasaDeviceSnapshot,
    cat: Cat,
    weight: float,
    unit: CatWeightUnit,
) -> None:
    """Save ``weight`` to the cat's profile, then read the profile back."""
    try:
        await entry.runtime_data.client.async_set_cat_weight(
            snapshot.device["device_name"],
            cat.id,
            weight,
            unit=unit,
            zone_seconds=_utc_offset_seconds(),
        )
    except NeakasaApiClientError as exc:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="set_cat_weight_failed",
            translation_placeholders={"cat_name": cat.name, "error": str(exc)},
        ) from exc
    await entry.runtime_data.coordinator.async_request_refresh()
