"""Sand-calibration number entity for a Neakasa litter box."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import EntityCategory

from ..entity import NeakasaDeviceEntity


class NeakasaCalibrateSandNumber(NeakasaDeviceEntity, NumberEntity):
    """Calibrate the sand-level sensor by submitting the current fill percentage."""

    _attr_translation_key = "calibrate_sand"
    _attr_icon = "mdi:tune-variant"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 10
    _attr_mode = NumberMode.SLIDER

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_calibrate_sand"

    @property
    def native_value(self) -> int | None:
        """Return the current sand percentage as the slider's starting point."""
        snap = self.snapshot
        return None if snap is None else snap.status.sand_percent

    async def async_set_native_value(self, value: float) -> None:
        """Submit the new calibration percentage."""
        snap = self.snapshot
        if snap is None:
            return
        client = self.coordinator.config_entry.runtime_data.client
        await client.async_calibrate_sand(snap.device["device_name"], int(value))
        self.apply_optimistic_status({"sand_percent": int(value)})
