"""Bucket-full binary sensor for a Neakasa litter box."""

from __future__ import annotations

import time
from collections import deque
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later

from ..const import LOGGER
from ..entity import NeakasaDeviceEntity

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import CALLBACK_TYPE

    from ..coordinator import NeakasaDataUpdateCoordinator


_WINDOW_SECONDS = 300
_MAJORITY_THRESHOLD = 0.8
_REEVAL_AFTER_SECONDS = 30


class NeakasaBucketFullBinarySensor(NeakasaDeviceEntity, BinarySensorEntity):
    """
    Whether the waste bucket is full and needs emptying.

    The raw signal flaps quickly during clean cycles, so a strict
    "consecutive True" rule never accumulates. Instead this sensor keeps
    a sliding window of the last ``_WINDOW_SECONDS`` of samples and
    promotes to ``on`` once at least ``_MAJORITY_THRESHOLD`` of them are
    ``True`` over a fully-filled window. A periodic re-evaluation runs
    every ``_REEVAL_AFTER_SECONDS`` so promotion still happens when the
    underlying signal goes quiet (no further pushes / polls) but stayed
    mostly ``True``. Any single ``False`` reading immediately clears a
    previously-stable ``on`` state.
    """

    _attr_translation_key = "bucket_full"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: NeakasaDataUpdateCoordinator,
        iot_id: str,
    ) -> None:
        """Initialise debouncing state."""
        super().__init__(coordinator, iot_id)
        self._stable_on: bool = False
        self._samples: deque[tuple[float, bool]] = deque()
        self._unsub_reeval: CALLBACK_TYPE | None = None

    @property
    def unique_id(self) -> str:
        """Return the stable unique id."""
        return f"{self.iot_id}_bucket_full"

    @property
    def is_on(self) -> bool | None:
        """Return the debounced bucket-full state."""
        if self.snapshot is None:
            return None
        return self._stable_on

    async def async_added_to_hass(self) -> None:
        """Bootstrap the debounce state machine from the current snapshot."""
        await super().async_added_to_hass()
        self._evaluate()
        self._schedule_reeval()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Re-evaluate dwell timing on every coordinator update."""
        self._evaluate()
        super()._handle_coordinator_update()

    @callback
    def _evaluate(self) -> None:
        """Append the latest sample and apply the majority rule."""
        snap = self.snapshot
        if snap is None:
            return
        raw = snap.status.bucket_full
        now = time.monotonic()
        self._samples.append((now, raw))
        cutoff = now - _WINDOW_SECONDS
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

        # Immediate clear: any False reading drops a confirmed-on state.
        if self._stable_on and not raw:
            LOGGER.debug(
                "bucket_full[%s] clearing on raw=False (was stable_on)",
                self.iot_id,
            )
            self._stable_on = False
            return

        # Need a fully-aged window to promote — i.e., the oldest sample
        # in the deque must be at least _WINDOW_SECONDS old (modulo a
        # small fudge to absorb sampling jitter).
        oldest_ts = self._samples[0][0]
        window_span = now - oldest_ts
        true_ratio = sum(1 for _, v in self._samples if v) / len(self._samples)
        LOGGER.debug(
            "bucket_full[%s] evaluate raw=%s span=%.1fs samples=%d "
            "true_ratio=%.2f stable=%s",
            self.iot_id,
            raw,
            window_span,
            len(self._samples),
            true_ratio,
            self._stable_on,
        )
        if (
            not self._stable_on
            and window_span >= _WINDOW_SECONDS - 1
            and true_ratio >= _MAJORITY_THRESHOLD
        ):
            LOGGER.debug(
                "bucket_full[%s] promoting to ON (ratio=%.2f)",
                self.iot_id,
                true_ratio,
            )
            self._stable_on = True

    @callback
    def _periodic_reeval(self, _now: datetime) -> None:
        """Periodically re-run ``_evaluate`` while ``raw`` is quiet."""
        self._unsub_reeval = None
        if self.snapshot is not None:
            self._evaluate()
            self.async_write_ha_state()
        self._schedule_reeval()

    @callback
    def _schedule_reeval(self) -> None:
        """Arm the periodic re-evaluation tick."""
        if self._unsub_reeval is not None:
            return
        self._unsub_reeval = async_call_later(
            self.hass, _REEVAL_AFTER_SECONDS, self._periodic_reeval
        )

    @callback
    def _cancel_reeval(self) -> None:
        """Drop the periodic re-evaluation tick."""
        if self._unsub_reeval is not None:
            self._unsub_reeval()
            self._unsub_reeval = None

    async def async_will_remove_from_hass(self) -> None:
        """Tear down the periodic tick when HA drops the entity."""
        self._cancel_reeval()
        await super().async_will_remove_from_hass()
