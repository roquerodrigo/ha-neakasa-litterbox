"""Needs-cleaning binary sensor for a Neakasa litter box."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from ..entity import NeakasaDeviceEntity


class NeakasaNeedsCleaningBinarySensor(NeakasaDeviceEntity, BinarySensorEntity):
    """Whether the device flagged itself as needing a clean."""

    _attr_translation_key = "needs_cleaning"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_needs_cleaning"

    @property
    def is_on(self) -> bool | None:
        """Return ``True`` if the box is signalling it needs cleaning."""
        snap = self.snapshot
        return None if snap is None else snap.status.needs_cleaning
