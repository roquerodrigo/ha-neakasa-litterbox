"""Bucket-full binary sensor for a Neakasa litter box."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from ..entity import NeakasaDeviceEntity


class NeakasaBucketFullBinarySensor(NeakasaDeviceEntity, BinarySensorEntity):
    """Whether the waste bucket is full and needs emptying."""

    _attr_translation_key = "bucket_full"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_bucket_full"

    @property
    def is_on(self) -> bool | None:
        """Return ``True`` when the device reports the waste bucket full."""
        snap = self.snapshot
        if snap is None:
            return None
        return snap.status.bucket_full
