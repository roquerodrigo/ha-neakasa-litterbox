"""Operating-state sensor for a Neakasa litter box."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from neakasa_litterbox_sdk import OperatingState

from ..entity import NeakasaDeviceEntity

# Option strings exposed to HA — also the keys under the translation
# ``state`` map. ``UNKNOWN`` is deliberately excluded: it maps to
# ``None`` so HA renders the standard "unknown" state.
_STATE_OPTIONS: list[str] = [
    OperatingState.IDLE.name.lower(),
    OperatingState.CLEANING.name.lower(),
    OperatingState.RESTORING.name.lower(),
    OperatingState.LEVELING.name.lower(),
]


class NeakasaOperatingStateSensor(NeakasaDeviceEntity, SensorEntity):
    """What the box is currently doing (idle / cleaning / restoring / leveling)."""

    _attr_translation_key = "operating_state"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = _STATE_OPTIONS

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_operating_state"

    @property
    def native_value(self) -> str | None:
        """Return the current activity as a lowercase option string."""
        snap = self.snapshot
        if snap is None:
            return None
        state = snap.status.operating_state
        if state is OperatingState.UNKNOWN:
            return None
        return state.name.lower()
