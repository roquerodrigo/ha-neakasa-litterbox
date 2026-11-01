"""Tracks which cloud activity records were already reported as events."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from collections.abc import Iterable

    from homeassistant.core import HomeAssistant
    from neakasa_litterbox_sdk import ToiletRecord

    from .data import NeakasaActivityCursors


_STORAGE_VERSION = 1
_SAVE_DELAY_SECONDS = 1


class NeakasaActivityRecordTracker:
    """
    Reports each finished cloud activity record once, across restarts.

    The cloud numbers every record type from its own sequence, so a single
    "last seen id" would hide newer records of the types with lower ids. One
    cursor per device and record type keeps the storage constant in size. A
    device seen for the first time only seeds its cursors: replaying the
    whole lookback window as new activity would be wrong.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Bind the tracker to the storage file of a config entry."""
        self._store: Store[NeakasaActivityCursors] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}.activity_records",
        )
        self._cursors: NeakasaActivityCursors = {}

    async def async_load(self) -> None:
        """Restore the cursors saved by a previous run."""
        self._cursors = await self._store.async_load() or {}

    async def async_save(self) -> None:
        """Write the cursors now, so a reload cannot read outdated ones."""
        await self._store.async_save(self._cursors)

    async def async_remove(self) -> None:
        """Delete the storage file."""
        await self._store.async_remove()

    def collect_new(
        self,
        iot_id: str,
        records: Iterable[ToiletRecord],
    ) -> list[ToiletRecord]:
        """Return the records not reported yet, oldest first, and advance cursors."""
        now = int(dt_util.utcnow().timestamp())
        finished = sorted(
            (r for r in records if r.start_time < r.end_time <= now),
            key=lambda r: r.record_id,
        )
        is_new_device = iot_id not in self._cursors
        cursors = self._cursors.setdefault(iot_id, {})
        new_records: list[ToiletRecord] = []
        for record in finished:
            record_type = str(record.record_type.value)
            if record.record_id > cursors.get(record_type, 0):
                cursors[record_type] = record.record_id
                new_records.append(record)
        if is_new_device:
            LOGGER.debug("Seeded activity cursors of %s: %s", iot_id, cursors)
            new_records = []
        if new_records:
            LOGGER.debug("New activity records of %s: %d", iot_id, len(new_records))
        if is_new_device or new_records:
            self._store.async_delay_save(lambda: self._cursors, _SAVE_DELAY_SECONDS)
        return sorted(new_records, key=lambda r: r.end_time)
