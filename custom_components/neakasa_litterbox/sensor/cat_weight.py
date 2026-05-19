"""Latest measured weight for a cat from the most recent litter box visit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfMass

from ..entity import NeakasaCatEntity

if TYPE_CHECKING:
    from ..data import NeakasaPayload


class NeakasaCatWeightSensor(NeakasaCatEntity, SensorEntity):
    """Weight measured by the device on this cat's most recent visit."""

    _attr_translation_key = "cat_weight"
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_cat_{self.cat_id}_weight"

    @property
    def native_value(self) -> float | None:
        """Return the weight from this cat's latest visit, or ``None``."""
        payload: NeakasaPayload | None = self.coordinator.data
        if payload is None:
            return None
        device = payload.devices.get(self.iot_id)
        if device is None:
            return None
        stats = device.cat_stats.get(self.cat_id)
        if stats is None:
            return None
        return stats["last_visit_weight"]
