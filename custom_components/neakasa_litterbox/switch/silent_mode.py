"""Silent-mode switch for a Neakasa litter box."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory

from ..entity import NeakasaDeviceEntity


class NeakasaSilentModeSwitch(NeakasaDeviceEntity, SwitchEntity):
    """Suppress beeps and other audible cues from the device."""

    _attr_translation_key = "silent_mode"
    _attr_icon = "mdi:volume-mute"
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_silent_mode"

    @property
    def is_on(self) -> bool | None:
        """Return ``True`` if silent mode is enabled."""
        snap = self.snapshot
        return None if snap is None else snap.status.silent_mode

    async def _set(self, *, enabled: bool) -> None:
        """Push the new state and optimistically reflect it locally."""
        snap = self.snapshot
        if snap is None:
            return
        client = self.coordinator.config_entry.runtime_data.client
        await client.async_set_silent_mode(snap.device["device_name"], enabled=enabled)
        self.apply_optimistic_status({"silent_mode": enabled})

    async def async_turn_on(self, **_kwargs: object) -> None:
        """Enable silent mode."""
        await self._set(enabled=True)

    async def async_turn_off(self, **_kwargs: object) -> None:
        """Disable silent mode."""
        await self._set(enabled=False)
