"""Level-now button for a Neakasa litter box."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from ..entity import NeakasaDeviceEntity


class NeakasaLevelNowButton(NeakasaDeviceEntity, ButtonEntity):
    """Trigger a manual sand-levelling cycle."""

    _attr_translation_key = "level_now"
    _attr_icon = "mdi:layers"

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_level_now"

    async def async_press(self) -> None:
        """Start a sand-levelling cycle."""
        snap = self.snapshot
        if snap is None:
            return
        client = self.coordinator.config_entry.runtime_data.client
        await client.async_start_level(snap.device["device_name"])
        await self.coordinator.async_request_refresh()
