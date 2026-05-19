"""Sand-level sensor for a Neakasa litter box."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE

from ..entity import NeakasaDeviceEntity


class NeakasaSandPercentSensor(NeakasaDeviceEntity, SensorEntity):
    """Current sand fill level as a percentage."""

    _attr_translation_key = "sand_percent"
    _attr_icon = "mdi:countertop"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_sand_percent"

    @property
    def native_value(self) -> int | None:
        """Return the sand fill percentage."""
        snap = self.snapshot
        return None if snap is None else snap.status.sand_percent
