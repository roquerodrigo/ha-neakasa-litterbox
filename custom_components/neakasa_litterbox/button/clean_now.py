"""Clean-now button for a Neakasa litter box."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from ..entity import NeakasaDeviceEntity


class NeakasaCleanNowButton(NeakasaDeviceEntity, ButtonEntity):
    """Trigger a manual clean cycle."""

    _attr_translation_key = "clean_now"
    _attr_icon = "mdi:broom"

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_clean_now"

    async def async_press(self) -> None:
        """Start a clean cycle."""
        snap = self.snapshot
        if snap is None:
            return
        client = self.coordinator.config_entry.runtime_data.client
        await client.async_start_clean(snap.device["device_name"])
        await self.coordinator.async_request_refresh()
