"""MQTT push client wiring the SDK status stream into the coordinator."""

from __future__ import annotations

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


class NeakasaPushClient:
    """Bridges the SDK :class:`StatusStream` into the HA coordinator."""

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

    async def async_start(self) -> None:
        """Open the MQTT stream; log and continue if push is unavailable."""
        if self._stream is not None:
            return
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
            return
        self._stream = stream
        LOGGER.debug("Neakasa push stream started")

    async def async_stop(self) -> None:
        """Close the MQTT stream; idempotent."""
        if self._stream is None:
            return
        try:
            await self._stream.stop()
        except Exception:  # noqa: BLE001 - shutdown should swallow any transport error
            LOGGER.debug("Push stream stop raised; ignoring", exc_info=True)
        finally:
            self._stream = None

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
