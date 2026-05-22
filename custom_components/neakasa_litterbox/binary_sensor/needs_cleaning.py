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
        """
        Return ``True`` if the box is signalling it needs cleaning.

        The SDK derives ``needs_cleaning`` from ``catLeft.needClean``, a
        device property the firmware only refreshes on cat exit — so the
        flag stays ``True`` after a clean cycle until the next visit.
        Cross-check the toilet-records timeline: if a clean (auto or
        manual) ran after the latest cat visit, treat the box as clean.
        """
        snap = self.snapshot
        if snap is None:
            return None
        if not snap.status.needs_cleaning:
            return False
        return not (
            snap.last_clean_at is not None
            and snap.last_visit_at is not None
            and snap.last_clean_at >= snap.last_visit_at
        )
