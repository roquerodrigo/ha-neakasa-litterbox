"""Base coordinator entities for Neakasa Litterbox."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER
from .coordinator import NeakasaDataUpdateCoordinator
from .data import NeakasaPayload

if TYPE_CHECKING:
    from collections.abc import Mapping

    from neakasa_litterbox_sdk import Cat

    from .data import NeakasaDeviceSnapshot


class NeakasaDeviceEntity(CoordinatorEntity[NeakasaDataUpdateCoordinator]):
    """Base entity bound to a single Neakasa litter box."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NeakasaDataUpdateCoordinator,
        iot_id: str,
    ) -> None:
        """Store the iot_id so the entity can find its snapshot lazily."""
        super().__init__(coordinator)
        self._iot_id = iot_id

    @property
    def iot_id(self) -> str:
        """Return the stable Aliyun iot_id of this litter box."""
        return self._iot_id

    @property
    def snapshot(self) -> NeakasaDeviceSnapshot | None:
        """Return the latest snapshot for this device, or ``None`` if absent."""
        payload: NeakasaPayload | None = self.coordinator.data
        if payload is None:
            return None
        return payload.devices.get(self._iot_id)

    @property
    def available(self) -> bool:
        """Mark the entity unavailable when its device drops from the payload."""
        return super().available and self.snapshot is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return DeviceInfo identifying this litter box."""
        snap = self.snapshot
        name = snap.device["product_name"] if snap else self._iot_id
        sw_version = snap.device["firmware_version"] if snap else None
        hw_version = snap.device["hardware_version"] if snap else None
        return DeviceInfo(
            identifiers={(DOMAIN, self._iot_id)},
            name=name,
            manufacturer=MANUFACTURER,
            model=snap.device["product_name"] if snap else None,
            sw_version=sw_version,
            hw_version=hw_version,
        )

    def apply_optimistic_status(
        self,
        changes: Mapping[str, bool | int | str],
    ) -> None:
        """
        Patch ``DeviceStatus`` locally so the UI reflects the change immediately.

        Use this right after sending a command. The MQTT push or the next
        polling cycle confirms (or corrects) the optimistic state — without
        this, an eager re-poll usually returns the pre-command state and the
        UI snaps back.
        """
        payload: NeakasaPayload | None = self.coordinator.data
        if payload is None:
            return
        snap = payload.devices.get(self._iot_id)
        if snap is None:
            return
        # mypy can't see that ``changes`` keys match DeviceStatus fields.
        new_status = dataclasses.replace(snap.status, **changes)  # type: ignore[arg-type]
        new_snap = dataclasses.replace(snap, status=new_status)
        new_payload = NeakasaPayload(
            devices={**payload.devices, self._iot_id: new_snap},
        )
        self.coordinator.async_set_updated_data(new_payload)


class NeakasaCatEntity(CoordinatorEntity[NeakasaDataUpdateCoordinator]):
    """Base entity bound to a Cat profile linked to a litter box."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NeakasaDataUpdateCoordinator,
        iot_id: str,
        cat_id: int,
    ) -> None:
        """Pin the entity to its parent device and cat id."""
        super().__init__(coordinator)
        self._iot_id = iot_id
        self._cat_id = cat_id

    @property
    def iot_id(self) -> str:
        """Return the parent litter box iot_id."""
        return self._iot_id

    @property
    def cat_id(self) -> int:
        """Return the SDK cat id this entity tracks."""
        return self._cat_id

    @property
    def cat(self) -> Cat | None:
        """Return the live Cat profile if still present, else ``None``."""
        payload: NeakasaPayload | None = self.coordinator.data
        if payload is None:
            return None
        device = payload.devices.get(self._iot_id)
        if device is None:
            return None
        return next((c for c in device.cats if c.id == self._cat_id), None)

    @property
    def available(self) -> bool:
        """Mark unavailable when the cat is no longer linked to the device."""
        return super().available and self.cat is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return DeviceInfo for this cat, anchored via_device to the litter box."""
        cat = self.cat
        name = cat.name if cat is not None else str(self._cat_id)
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._iot_id}-cat-{self._cat_id}")},
            via_device=(DOMAIN, self._iot_id),
            name=name,
            manufacturer=MANUFACTURER,
        )
