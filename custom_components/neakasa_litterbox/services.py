"""Service actions that write to the Neakasa cloud."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Literal, cast

import probatio
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import service
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .device_identity import cat_identifier
from .exceptions import NeakasaApiClientError

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import AnyDeviceEntry
    from neakasa_litterbox_sdk import Cat

    from .data import NeakasaConfigEntry, NeakasaDeviceSnapshot

SERVICE_SET_CAT_WEIGHT = "set_cat_weight"

ATTR_WEIGHT = "weight"
ATTR_UNIT = "unit"

WEIGHT_UNITS: tuple[str, ...] = ("kg", "lb")

SET_CAT_WEIGHT_SCHEMA = probatio.Schema(
    {
        probatio.Required(ATTR_DEVICE_ID): cv.string,
        probatio.Required(ATTR_WEIGHT): probatio.All(
            probatio.Coerce(float),
            probatio.Range(min=0, min_included=False),
        ),
        probatio.Required(ATTR_UNIT): probatio.In(WEIGHT_UNITS),
    }
)


def _find_cat(
    entry: NeakasaConfigEntry,
    device: AnyDeviceEntry,
) -> tuple[NeakasaDeviceSnapshot, Cat]:
    """Return the litter box and cat profile a cat device stands for."""
    identifiers = {
        identifier for domain, identifier in device.identifiers if domain == DOMAIN
    }
    for iot_id, snapshot in entry.runtime_data.coordinator.data.devices.items():
        for cat in snapshot.cats:
            if cat_identifier(iot_id, cat.id) in identifiers:
                return snapshot, cat
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="not_a_cat",
        translation_placeholders={
            "device_name": device.name_by_user or device.name or device.id
        },
    )


def _utc_offset_seconds() -> int:
    """Return the offset of Home Assistant's time zone from UTC, in seconds."""
    return int((dt_util.now().utcoffset() or timedelta()).total_seconds())


async def _async_set_cat_weight(call: ServiceCall) -> None:
    """Save a weight to the profile of the cat device the call names."""
    device, entry = service.async_get_device_and_config_entry(
        call.hass,
        DOMAIN,
        call.data[ATTR_DEVICE_ID],
    )
    entry = cast("NeakasaConfigEntry", entry)
    snapshot, cat = _find_cat(entry, device)
    try:
        await entry.runtime_data.client.async_set_cat_weight(
            snapshot.device["device_name"],
            cat.id,
            call.data[ATTR_WEIGHT],
            unit=cast("Literal['kg', 'lb']", call.data[ATTR_UNIT]),
            zone_seconds=_utc_offset_seconds(),
        )
    except NeakasaApiClientError as exc:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="set_cat_weight_failed",
            translation_placeholders={"cat_name": cat.name, "error": str(exc)},
        ) from exc
    await entry.runtime_data.coordinator.async_request_refresh()


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration's service actions."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CAT_WEIGHT,
        _async_set_cat_weight,
        schema=SET_CAT_WEIGHT_SCHEMA,
    )
