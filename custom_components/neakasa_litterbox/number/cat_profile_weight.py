"""Profile weight number entity for a cat linked to a Neakasa litter box."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfMass
from homeassistant.helpers.entity import EntityCategory

from ..cat_profile_weight import (
    async_save_cat_weight,
    cat_weight_unit,
    normalize_weight_unit,
)
from ..entity import NeakasaCatEntity


class NeakasaCatProfileWeightNumber(NeakasaCatEntity, NumberEntity):
    """Weight saved in the cat's profile, which the box uses to recognize it."""

    _attr_translation_key = "cat_profile_weight"
    _attr_device_class = NumberDeviceClass.WEIGHT
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0.1
    _attr_native_max_value = 100
    _attr_native_step = 0.1

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_cat_{self.cat_id}_profile_weight"

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the profile's unit, falling back to kg."""
        cat = self.cat
        unit = normalize_weight_unit(cat.unit) if cat is not None else None
        return unit or UnitOfMass.KILOGRAMS

    @property
    def native_value(self) -> float | None:
        """Return the profile weight, or ``None`` while the profile has none."""
        cat = self.cat
        if cat is None or cat.weight <= 0:
            return None
        return cat.weight

    async def async_set_native_value(self, value: float) -> None:
        """Save the new weight to the cat's profile."""
        snapshot = self.snapshot
        cat = self.cat
        if snapshot is None or cat is None:
            return
        await async_save_cat_weight(
            self.coordinator.config_entry,
            snapshot,
            cat,
            round(value, 2),
            cat_weight_unit(self.native_unit_of_measurement),
        )
