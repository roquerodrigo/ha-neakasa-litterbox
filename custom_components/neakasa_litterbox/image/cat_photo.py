"""Photo of a cat, as set in the mobile app."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.image import ImageEntity
from homeassistant.core import callback
from homeassistant.util import dt as dt_util

from ..entity import NeakasaCatEntity

if TYPE_CHECKING:
    from datetime import datetime

    from ..coordinator import NeakasaDataUpdateCoordinator


class NeakasaCatPhotoImage(NeakasaCatEntity, ImageEntity):
    """Photo of a cat, downloaded from the Neakasa cloud."""

    _attr_translation_key = "cat_photo"

    def __init__(
        self,
        coordinator: NeakasaDataUpdateCoordinator,
        iot_id: str,
        cat_id: int,
    ) -> None:
        """Bind to the cat and note the photo it currently has."""
        super().__init__(coordinator, iot_id, cat_id)
        ImageEntity.__init__(self, coordinator.hass, verify_ssl=True)
        self._photo_path = ""
        self._photo_updated_at: datetime | None = None
        self._note_current_photo()

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_cat_{self.cat_id}_photo"

    @property
    def image_url(self) -> str | None:
        """Return the latest signed URL of the photo, or ``None`` without one."""
        cat = self.cat
        return cat.avatar or None if cat is not None else None

    @property
    def image_last_updated(self) -> datetime | None:
        """Return when this entity first saw the current photo."""
        return self._photo_updated_at

    @callback
    def _handle_coordinator_update(self) -> None:
        """Pick up a replaced photo before publishing the new state."""
        self._note_current_photo()
        super()._handle_coordinator_update()

    def _note_current_photo(self) -> None:
        """Drop the downloaded photo once the cloud reports a different one."""
        cat = self.cat
        if cat is None or cat.path == self._photo_path:
            return
        self._photo_path = cat.path
        self._photo_updated_at = dt_util.utcnow() if cat.path else None
        self._cached_image = None
