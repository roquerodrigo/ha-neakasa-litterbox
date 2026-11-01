"""Base entity bound to a Cat profile linked to a litter box."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import ChildDeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import ATTRIBUTION, DOMAIN
from ..coordinator import NeakasaDataUpdateCoordinator
from ..device_identity import cat_identifier

if TYPE_CHECKING:
    from neakasa_litterbox_sdk import Cat

    from ..data import NeakasaPayload


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
    def device_info(self) -> ChildDeviceInfo:
        """
        Return this cat as a child device of its litter box.

        Platforms are forwarded concurrently and a child device needs its parent
        registered first, so the litter box is created here if none of its own
        entities got to it yet.
        """
        cat = self.cat
        litter_box = dr.async_get(self.hass).async_get_or_create(
            config_entry_id=self.coordinator.config_entry.entry_id,
            identifiers={(DOMAIN, self._iot_id)},
        )
        return ChildDeviceInfo(
            identifiers={(DOMAIN, cat_identifier(self._iot_id, self._cat_id))},
            parent_device_id=litter_box.id,
            name=cat.name if cat is not None else str(self._cat_id),
        )
