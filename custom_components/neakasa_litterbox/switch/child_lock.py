"""Child-lock switch for a Neakasa litter box."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory

from ..entity import NeakasaDeviceEntity


class NeakasaChildLockSwitch(NeakasaDeviceEntity, SwitchEntity):
    """Lock the on-device controls to prevent accidental input."""

    _attr_translation_key = "child_lock"
    _attr_icon = "mdi:lock"
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_child_lock"

    @property
    def is_on(self) -> bool | None:
        """Return ``True`` if the child lock is engaged."""
        snap = self.snapshot
        return None if snap is None else snap.status.child_lock

    async def _set(self, *, enabled: bool) -> None:
        """Push the new state and optimistically reflect it locally."""
        snap = self.snapshot
        if snap is None:
            return
        client = self.coordinator.config_entry.runtime_data.client
        await client.async_set_child_lock(snap.device["device_name"], enabled=enabled)
        self.apply_optimistic_status({"child_lock": enabled})

    async def async_turn_on(self, **_kwargs: object) -> None:
        """Engage the child lock."""
        await self._set(enabled=True)

    async def async_turn_off(self, **_kwargs: object) -> None:
        """Release the child lock."""
        await self._set(enabled=False)
