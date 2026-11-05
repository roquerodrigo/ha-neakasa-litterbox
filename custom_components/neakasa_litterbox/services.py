"""Service actions that write to the Neakasa cloud."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import probatio
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import service

from .cat_profile_weight import CAT_WEIGHT_UNITS, async_save_cat_weight
from .const import DOMAIN
from .device_identity import cat_identifier

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import AnyDeviceEntry
    from neakasa_litterbox_sdk import Cat

    from .cat_profile_weight import CatWeightUnit
    from .data import NeakasaConfigEntry, NeakasaDeviceSnapshot

SERVICE_SET_CAT_WEIGHT = "set_cat_weight"

ATTR_WEIGHT = "weight"
ATTR_UNIT = "unit"

SET_CAT_WEIGHT_SCHEMA = probatio.Schema(
    {
        probatio.Required(ATTR_DEVICE_ID): cv.string,
        probatio.Required(ATTR_WEIGHT): probatio.All(
            probatio.Coerce(float),
            probatio.Range(min=0, min_included=False),
        ),
        probatio.Required(ATTR_UNIT): probatio.In(CAT_WEIGHT_UNITS),
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


async def _async_set_cat_weight(call: ServiceCall) -> None:
    """Save a weight to the profile of the cat device the call names."""
    device, entry = service.async_get_device_and_config_entry(
        call.hass,
        DOMAIN,
        call.data[ATTR_DEVICE_ID],
    )
    entry = cast("NeakasaConfigEntry", entry)
    snapshot, cat = _find_cat(entry, device)
    await async_save_cat_weight(
        entry,
        snapshot,
        cat,
        call.data[ATTR_WEIGHT],
        cast("CatWeightUnit", call.data[ATTR_UNIT]),
    )


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration's service actions."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CAT_WEIGHT,
        _async_set_cat_weight,
        schema=SET_CAT_WEIGHT_SCHEMA,
    )
