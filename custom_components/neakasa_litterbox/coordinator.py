"""DataUpdateCoordinator for neakasa_litterbox."""

from __future__ import annotations

import asyncio
import dataclasses
from collections import defaultdict
from typing import TYPE_CHECKING

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from neakasa_litterbox_sdk import OperatingState, RecordType

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
    NeakasaApiClientCommunicationError,
    NeakasaApiClientDeviceBusyError,
    NeakasaApiClientError,
    NeakasaApiClientSessionExpiredError,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from datetime import timedelta

    from homeassistant.core import HomeAssistant
    from neakasa_litterbox_sdk import Cat, Device, DeviceStatus, ToiletRecord

    from .data import NeakasaConfigEntry


_TRANSIENT_RETRY_ATTEMPTS = 3
_TRANSIENT_RETRY_BASE_DELAY = 2.0


class NeakasaDataUpdateCoordinator(DataUpdateCoordinator[NeakasaPayload]):
    """Polls Neakasa devices and aggregates per-device snapshots."""

    config_entry: NeakasaConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: NeakasaConfigEntry,
        scan_interval: timedelta,
    ) -> None:
        """Initialize."""
        self.leveling_events: dict[str, list[int]] = {}
        self.leveling_durations: dict[str, dict[int, int]] = {}
        self.leveling_state_callback: (
            Callable[[str, OperatingState, OperatingState], None] | None
        ) = None
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            config_entry=entry,
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

    async def _async_update_data(self) -> NeakasaPayload:  # noqa: PLR0912
        """
        Fetch devices, status, cats and records in parallel per device.

        Transient transport errors (DNS hiccups, TLS handshake retries
        against the cloud) get one or two short retries instead of
        immediately marking entities unavailable until the next 10-min
        scan window. An expired session buys one silent sign-in: the
        cloud drops it whenever the account signs in elsewhere (the
        mobile app, another client) and the stored credentials are still
        good, so a reauth flow would only ask for what we already have.
        """
        client = self.config_entry.runtime_data.client
        transport_failures = 0
        signed_in_again = False
        while True:
            try:
                devices = await client.async_list_devices()
                snapshots = await asyncio.gather(
                    *(self._fetch_device_snapshot(device) for device in devices),
                )
            except NeakasaApiClientSessionExpiredError as exc:
                if signed_in_again:
                    raise ConfigEntryAuthFailed(str(exc)) from exc
                signed_in_again = True
                LOGGER.debug("Cloud session expired (%s); signing in again", exc)
                await self._async_sign_in_again()
                continue
            except NeakasaApiClientAuthenticationError as exc:
                raise ConfigEntryAuthFailed(str(exc)) from exc
            except NeakasaApiClientDeviceBusyError as exc:
                # Device is mid-cycle; the cloud refuses the readback. Keep
                # the last snapshot available — MQTT pushes overlay the live
                # operating_state — instead of flapping entities to
                # unavailable. First-ever poll has nothing to fall back on.
                if self.data is not None:
                    LOGGER.debug(
                        "Device busy mid-cycle; keeping last snapshot (%s)", exc
                    )
                    return self.data
                raise UpdateFailed(str(exc)) from exc
            except NeakasaApiClientCommunicationError as exc:
                transport_failures += 1
                if transport_failures >= _TRANSIENT_RETRY_ATTEMPTS:
                    raise UpdateFailed(str(exc)) from exc
                delay = _TRANSIENT_RETRY_BASE_DELAY * (2 ** (transport_failures - 1))
                LOGGER.debug(
                    "Transient comms error on attempt %d/%d (%s); retry in %.1fs",
                    transport_failures,
                    _TRANSIENT_RETRY_ATTEMPTS,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
                continue
            except NeakasaApiClientError as exc:
                raise UpdateFailed(str(exc)) from exc
            for snap in snapshots:
                current = (
                    self.data.devices.get(snap.device["iot_id"])
                    if self.data is not None
                    else None
                )
                if current is not None:
                    old_state = current.status.operating_state
                    new_state = snap.status.operating_state
                    if old_state != new_state:
                        LOGGER.info(
                            "Neakasa cloud poll state for %s: %s -> %s",
                            snap.device["device_name"],
                            old_state,
                            new_state,
                        )
                    if self.leveling_state_callback is not None:
                        self.leveling_state_callback(
                            snap.device["iot_id"], old_state, new_state
                        )
            return NeakasaPayload(
                devices={
                    snap.device["iot_id"]: dataclasses.replace(
                        snap,
                        leveling_events=tuple(
                            self.leveling_events.get(snap.device["iot_id"], [])
                        ),
                        leveling_durations=self.leveling_durations.get(
                            snap.device["iot_id"], {}
                        ),
                    )
                    for snap in snapshots
                },
            )

    async def _async_sign_in_again(self) -> None:
        """Re-establish the cloud session with the credentials on the entry."""
        client = self.config_entry.runtime_data.client
        try:
            await client.async_login()
        except NeakasaApiClientAuthenticationError as exc:
            raise ConfigEntryAuthFailed(str(exc)) from exc
        except NeakasaApiClientError as exc:
            raise UpdateFailed(str(exc)) from exc

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
    unique_records = list({r.record_id: r for r in records}.values())
    visit_records = [r for r in unique_records if r.record_type == RecordType.CAT_VISIT]
    clean_records = [
        r for r in unique_records if r.record_type == RecordType.CLEAN_CYCLE
    ]
    today_start = int(dt_util.start_of_local_day().timestamp())

    todays_visits = [r for r in visit_records if r.start_time >= today_start]
    visits_today = len(todays_visits)
    last_visit_at = max((r.start_time for r in visit_records), default=None)
    last_clean_at = max((r.end_time for r in clean_records), default=None)

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
            last_visit_weight_unit=latest.unit if latest is not None else None,
            visits_today=len(todays),
            stay_today_seconds=sum(
                max(
                    0,
                    min(r.end_time, int(dt_util.utcnow().timestamp()))
                    - max(r.start_time, today_start),
                )
                for r in cat_records
                if r.end_time > today_start
            ),
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
        last_clean_at=last_clean_at,
        cat_stats=cat_stats,
        recent_records=tuple(
            sorted(
                (
                    record
                    for record in unique_records
                    if record.record_type
                    in (RecordType.CAT_VISIT, RecordType.CLEAN_CYCLE)
                ),
                key=lambda record: (record.start_time, record.record_id),
                reverse=True,
            )[:30]
        ),
    )


def scan_interval_from_options(options: Mapping[str, int]) -> int:
    """Return the configured polling interval (seconds) with a sane default."""
    return int(options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS))
