"""DataUpdateCoordinator for neakasa_litterbox."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import TYPE_CHECKING

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from neakasa_litterbox_sdk import RecordType

from .const import (
    CONF_STATISTICS_LOOKBACK_DAYS,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DEFAULT_STATISTICS_LOOKBACK_DAYS,
    DOMAIN,
    LOGGER,
)
from .data import (
    NeakasaCatStats,
    NeakasaDeviceInfo,
    NeakasaDeviceSnapshot,
    NeakasaPayload,
)
from .exceptions import (
    NeakasaApiClientAuthenticationError,
    NeakasaApiClientError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import timedelta

    from homeassistant.core import HomeAssistant
    from neakasa_litterbox_sdk import Cat, Device, DeviceStatus, ToiletRecord

    from .data import NeakasaConfigEntry


class NeakasaDataUpdateCoordinator(DataUpdateCoordinator[NeakasaPayload]):
    """Polls Neakasa devices and aggregates per-device snapshots."""

    config_entry: NeakasaConfigEntry

    def __init__(self, hass: HomeAssistant, scan_interval: timedelta) -> None:
        """Initialize."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=scan_interval,
            always_update=False,
        )

    @property
    def _lookback_days(self) -> int:
        """Return the per-device record lookback (days) from options."""
        return int(
            self.config_entry.options.get(
                CONF_STATISTICS_LOOKBACK_DAYS,
                DEFAULT_STATISTICS_LOOKBACK_DAYS,
            ),
        )

    async def _async_update_data(self) -> NeakasaPayload:
        """Fetch devices, status, cats and records in parallel per device."""
        client = self.config_entry.runtime_data.client
        try:
            devices = await client.async_list_devices()
            snapshots = await asyncio.gather(
                *(self._fetch_device_snapshot(device) for device in devices),
            )
        except NeakasaApiClientAuthenticationError as exc:
            raise ConfigEntryAuthFailed(str(exc)) from exc
        except NeakasaApiClientError as exc:
            raise UpdateFailed(str(exc)) from exc

        return NeakasaPayload(
            devices={snap.device["iot_id"]: snap for snap in snapshots},
        )

    async def _fetch_device_snapshot(
        self,
        device: Device,
    ) -> NeakasaDeviceSnapshot:
        """Fetch status + cats + records for a single device in parallel."""
        client = self.config_entry.runtime_data.client
        now = dt_util.utcnow()
        end_time = int(now.timestamp())
        start_time = end_time - self._lookback_days * 86400

        status, cats, records = await asyncio.gather(
            client.async_get_status(device.device_name),
            client.async_list_cats(device.device_name),
            client.async_get_toilet_records(device.device_name, start_time, end_time),
        )

        return _build_snapshot(device, status, cats, records)


def _build_snapshot(
    device: Device,
    status: DeviceStatus,
    cats: list[Cat],
    records: list[ToiletRecord],
) -> NeakasaDeviceSnapshot:
    """Aggregate the raw SDK payloads into a snapshot consumed by entities."""
    visit_records = [r for r in records if r.record_type == RecordType.CAT_VISIT]
    today_start = int(dt_util.start_of_local_day().timestamp())

    todays_visits = [r for r in visit_records if r.start_time >= today_start]
    visits_today = len(todays_visits)
    last_visit_at = max((r.start_time for r in visit_records), default=None)

    by_cat: dict[int, list[ToiletRecord]] = defaultdict(list)
    for record in visit_records:
        by_cat[record.cat_id].append(record)

    cat_stats: dict[int, NeakasaCatStats] = {}
    for cat in cats:
        cat_records = by_cat.get(cat.id, [])
        todays = [r for r in cat_records if r.start_time >= today_start]
        latest = max(cat_records, key=lambda r: r.start_time, default=None)
        cat_stats[cat.id] = NeakasaCatStats(
            last_visit_at=latest.start_time if latest is not None else None,
            last_visit_weight=latest.weight if latest is not None else None,
            visits_today=len(todays),
        )

    info: NeakasaDeviceInfo = {
        "iot_id": device.iot_id,
        "device_name": device.device_name,
        # SDK returns model names with underscores (e.g. ``Neakasa_M1``); HA
        # device cards look cleaner with the spaced version.
        "product_name": device.product_name.replace("_", " "),
        "firmware_version": status.firmware_version,
        "hardware_version": status.hardware_version,
    }
    return NeakasaDeviceSnapshot(
        device=info,
        status=status,
        cats=tuple(cats),
        visits_today=visits_today,
        last_visit_at=last_visit_at,
        cat_stats=cat_stats,
    )


def scan_interval_from_options(options: Mapping[str, int]) -> int:
    """Return the configured polling interval (seconds) with a sane default."""
    return int(options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS))
