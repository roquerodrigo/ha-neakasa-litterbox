"""MQTT push client wiring the SDK status stream into the coordinator."""

from __future__ import annotations

import asyncio
import dataclasses
from typing import TYPE_CHECKING

from neakasa_litterbox_sdk import DeviceStatus

from .const import LOGGER
from .data import NeakasaPayload

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from neakasa_litterbox_sdk import StatusStream, StatusUpdate

    from .api import NeakasaApiClient
    from .coordinator import NeakasaDataUpdateCoordinator


_STATUS_FIELDS: frozenset[str] = frozenset(
    f.name for f in dataclasses.fields(DeviceStatus)
)

_INITIAL_BACKOFF_SECONDS = 5.0
_MAX_BACKOFF_SECONDS = 300.0
# How often the supervisor polls the SDK's dispatch task for liveness.
_HEALTH_CHECK_INTERVAL_SECONDS = 15.0
# A connection that survives this long resets the reconnect backoff.
_STABLE_UPTIME_SECONDS = 60.0


class NeakasaPushClient:
    """
    Bridges the SDK :class:`StatusStream` into the HA coordinator.

    Maintains a single live stream and respawns it with exponential
    backoff when the underlying MQTT dispatcher dies — the SDK doesn't
    surface disconnects on its public API, so the supervisor watches the
    transport's dispatch task to detect them and triggers a coordinator
    refresh after each recovery.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api: NeakasaApiClient,
        coordinator: NeakasaDataUpdateCoordinator,
    ) -> None:
        """Bind the push client to the active coordinator and SDK client."""
        self._hass = hass
        self._api = api
        self._coordinator = coordinator
        self._stream: StatusStream | None = None
        self._supervisor: asyncio.Task[None] | None = None
        self._stopping: bool = False

    async def async_start(self) -> None:
        """Open the MQTT stream and start the reconnect supervisor."""
        if self._supervisor is not None:
            return
        self._stopping = False
        # First attempt happens inline so a setup-time failure surfaces
        # before we hand off to the background supervisor.
        await self._connect_once()
        self._supervisor = asyncio.create_task(
            self._supervise(),
            name="neakasa_litterbox.push_supervisor",
        )

    async def async_stop(self) -> None:
        """Stop the supervisor and tear down the live stream. Idempotent."""
        self._stopping = True
        supervisor, self._supervisor = self._supervisor, None
        if supervisor is not None:
            supervisor.cancel()
        await self._close_stream()

    async def _connect_once(self) -> bool:
        """Try to open the stream once; log and continue on failure."""
        if self._stream is not None:
            return True
        # ``tls_insecure=True`` lets the MQTT TLS handshake succeed without a
        # locally-trusted CA bundle; the Neakasa broker still uses TLS, only
        # certificate validation is skipped.
        stream = self._api.watch_status(tls_insecure=True)
        stream.on_change(self._handle_change)
        try:
            await stream.start()
        except Exception:  # noqa: BLE001 - any push start failure degrades to polling-only
            LOGGER.warning(
                "Push stream failed to start; integration will rely on polling",
                exc_info=True,
            )
            return False
        self._stream = stream
        LOGGER.debug("Neakasa push stream started")
        return True

    async def _supervise(self) -> None:
        """Reconnect with exponential backoff whenever the stream dies."""
        backoff = _INITIAL_BACKOFF_SECONDS
        loop = asyncio.get_running_loop()
        while not self._stopping:
            if self._stream is None:
                if not await self._connect_once():
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)
                    continue
                # Catch up on anything missed during the outage.
                self._hass.async_create_task(
                    self._coordinator.async_request_refresh(),
                )
            connected_at = loop.time()
            await self._wait_for_stream_death()
            if self._stopping:
                return  # type: ignore[unreachable]
            await self._close_stream()
            uptime = loop.time() - connected_at
            if uptime >= _STABLE_UPTIME_SECONDS:
                backoff = _INITIAL_BACKOFF_SECONDS
            else:
                backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)
            LOGGER.info(
                "Push stream disconnected after %.0fs; reconnecting in %.0fs",
                uptime,
                backoff,
            )
            await asyncio.sleep(backoff)

    async def _wait_for_stream_death(self) -> None:
        """Block until the MQTT dispatcher task ends (or stop is requested)."""
        while not self._stopping:
            stream = self._stream
            if stream is None:
                return
            dispatch_task = _dispatch_task(stream)
            if isinstance(dispatch_task, asyncio.Task) and dispatch_task.done():
                return
            await asyncio.sleep(_HEALTH_CHECK_INTERVAL_SECONDS)

    async def _close_stream(self) -> None:
        """Stop the active stream, swallowing teardown errors."""
        stream, self._stream = self._stream, None
        if stream is None:
            return
        try:
            await stream.stop()
        except Exception:  # noqa: BLE001 - shutdown should swallow any transport error
            LOGGER.debug("Push stream stop raised; ignoring", exc_info=True)

    def _handle_change(self, update: StatusUpdate) -> None:
        """Merge an MQTT delta into the coordinator's last payload."""
        payload: NeakasaPayload | None = self._coordinator.data
        if payload is None:
            return
        target = next(
            (
                snap
                for snap in payload.devices.values()
                if snap.device["device_name"] == update.device_name
            ),
            None,
        )
        if target is None:
            return
        # SDK fans the ``StatusUpdate`` payload into a generic JSON shape; we
        # filter to known ``DeviceStatus`` fields whose values are always
        # str/int/bool per the dataclass schema before handing them off.
        patch: dict[str, bool | int | str] = {
            key: value
            for key, value in update.changes.items()
            if key in _STATUS_FIELDS and isinstance(value, (bool, int, str))
        }
        if not patch:
            return
        # ``patch`` was filtered to DeviceStatus fields above; mypy can't see it.
        new_status = dataclasses.replace(target.status, **patch)  # type: ignore[arg-type]
        new_snapshot = dataclasses.replace(target, status=new_status)
        new_payload = NeakasaPayload(
            devices={
                **payload.devices,
                target.device["iot_id"]: new_snapshot,
            },
        )
        self._coordinator.async_set_updated_data(new_payload)


def _dispatch_task(stream: StatusStream) -> object | None:
    """
    Return the SDK transport's dispatch task, or ``None`` if not exposed.

    The SDK doesn't publish disconnect events; the supervisor inspects
    this private task to drive reconnects. ``getattr`` guards against
    the SDK reshaping internals — when that happens auto-reconnect
    degrades to no-op rather than crashing.
    """
    transport = getattr(stream, "_transport", None)
    if transport is None:
        return None
    return getattr(transport, "_dispatch_task", None)
