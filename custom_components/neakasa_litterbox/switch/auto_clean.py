"""Auto-clean switch for a Neakasa litter box."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory

from ..entity import NeakasaDeviceEntity


class NeakasaAutoCleanSwitch(NeakasaDeviceEntity, SwitchEntity):
    """Toggle the scheduled automatic clean cycle."""

    _attr_translation_key = "auto_clean"
    _attr_icon = "mdi:broom"
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_auto_clean"

    @property
    def is_on(self) -> bool | None:
        """Return ``True`` if auto-clean is enabled."""
        snap = self.snapshot
        return None if snap is None else snap.status.cleaning_enabled

    async def _set(self, *, enabled: bool) -> None:
        """Push the new state and optimistically reflect it locally."""
        snap = self.snapshot
        if snap is None:
            return
        client = self.coordinator.config_entry.runtime_data.client
        await client.async_set_auto_clean(snap.device["device_name"], enabled=enabled)
        self.apply_optimistic_status({"cleaning_enabled": enabled})

    async def async_turn_on(self, **_kwargs: object) -> None:
        """Enable auto-clean."""
        await self._set(enabled=True)

    async def async_turn_off(self, **_kwargs: object) -> None:
        """Disable auto-clean."""
        await self._set(enabled=False)
