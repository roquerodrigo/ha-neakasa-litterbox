"""Visits-today aggregate sensor for a Neakasa litter box."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass

from ..entity import NeakasaDeviceEntity


class NeakasaVisitsTodaySensor(NeakasaDeviceEntity, SensorEntity):
    """Number of cat visits recorded since the start of the local day."""

    _attr_translation_key = "visits_today"
    _attr_icon = "mdi:cat"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_visits_today"

    @property
    def native_value(self) -> int | None:
        """Return the number of visits since midnight."""
        snap = self.snapshot
        return None if snap is None else snap.visits_today
