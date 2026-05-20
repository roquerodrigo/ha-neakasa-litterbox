"""Neakasa Litterbox API client (wraps the neakasa-litterbox-sdk)."""

from __future__ import annotations

import contextlib
from contextlib import contextmanager
from typing import TYPE_CHECKING

from neakasa_litterbox_sdk import (
    ApiError,
    AuthenticationError,
    InvalidCredentialsError,
    NeakasaClient,
    NeakasaError,
    Region,
    SessionExpiredError,
    TransportError,
)

from .exceptions import (
    NeakasaApiClientAuthenticationError,
    NeakasaApiClientCommunicationError,
    NeakasaApiClientError,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from neakasa_litterbox_sdk import (
        Cat,
        DailyStatistics,
        Device,
        DeviceStatus,
        StatusStream,
        ToiletRecord,
    )


@contextmanager
def _translate_errors() -> Iterator[None]:
    """Map SDK exceptions to the integration's hierarchy."""
    try:
        yield
    except (InvalidCredentialsError, SessionExpiredError, AuthenticationError) as exc:
        raise NeakasaApiClientAuthenticationError(str(exc)) from exc
    except TransportError as exc:
        raise NeakasaApiClientCommunicationError(str(exc)) from exc
    except (ApiError, NeakasaError) as exc:
        raise NeakasaApiClientError(str(exc)) from exc


class NeakasaApiClient:
    """Async client for the Neakasa cloud, wrapping the SDK NeakasaClient."""

    def __init__(
        self,
        username: str,
        password: str,
        region: str,
        timeout: float = 10.0,
    ) -> None:
        """Build a client bound to ``region`` (US/EU/AP)."""
        try:
            sdk_region = Region[region.upper()]
        except KeyError as exc:
            msg = f"Unknown Neakasa region: {region}"
            raise NeakasaApiClientError(msg) from exc
        self._client = NeakasaClient(
            email=username,
            password=password,
            region=sdk_region,
            timeout=timeout,
        )

    @property
    def sdk(self) -> NeakasaClient:
        """Expose the underlying SDK client (read-only)."""
        return self._client

    async def async_login(self) -> None:
        """Establish a session against the Neakasa cloud."""
        with _translate_errors():
            await self._client.login()

    async def async_close(self) -> None:
        """Tear down the underlying session, swallowing SDK errors."""
        with contextlib.suppress(NeakasaError):
            await self._client.close()

    async def async_list_devices(self) -> list[Device]:
        """Return every litter box bound to the authenticated account."""
        with _translate_errors():
            return await self._client.list_devices()

    async def async_get_status(self, device_name: str) -> DeviceStatus:
        """Return the live status snapshot for a device."""
        with _translate_errors():
            return await self._client.get_status(device_name)

    async def async_list_cats(self, device_name: str) -> list[Cat]:
        """Return the cat profiles attached to a device."""
        with _translate_errors():
            return await self._client.list_cats(device_name)

    async def async_get_toilet_records(
        self,
        device_name: str,
        start_time: int,
        end_time: int,
    ) -> list[ToiletRecord]:
        """Return raw toilet records in the given epoch-seconds window."""
        with _translate_errors():
            return await self._client.get_toilet_records(
                device_name, start_time, end_time
            )

    async def async_get_toilet_statistics(
        self,
        device_name: str,
        start_time: int,
        end_time: int,
        *,
        zone_seconds: int = 0,
    ) -> list[DailyStatistics]:
        """Return per-day aggregates over the given window."""
        with _translate_errors():
            return await self._client.get_toilet_statistics(
                device_name, start_time, end_time, zone_seconds=zone_seconds
            )

    async def async_start_clean(self, device_name: str) -> None:
        """Trigger a manual clean cycle."""
        with _translate_errors():
            await self._client.start_clean(device_name)

    async def async_stop_clean(self, device_name: str) -> None:
        """Abort a running clean cycle."""
        with _translate_errors():
            await self._client.stop_clean(device_name)

    async def async_start_level(self, device_name: str) -> None:
        """Trigger a manual sand-level operation."""
        with _translate_errors():
            await self._client.start_level(device_name)

    async def async_stop_level(self, device_name: str) -> None:
        """Abort a running sand-level operation."""
        with _translate_errors():
            await self._client.stop_level(device_name)

    async def async_calibrate_sand(self, device_name: str, percent: int) -> None:
        """Calibrate the sand sensor to ``percent`` (0-100)."""
        with _translate_errors():
            await self._client.calibrate_sand(device_name, percent)

    async def async_set_auto_clean(self, device_name: str, *, enabled: bool) -> None:
        """Enable or disable automatic cleaning."""
        with _translate_errors():
            await self._client.set_auto_clean(device_name, enabled)

    async def async_set_auto_level(self, device_name: str, *, enabled: bool) -> None:
        """Enable or disable automatic levelling."""
        with _translate_errors():
            await self._client.set_auto_level(device_name, enabled)

    async def async_set_silent_mode(self, device_name: str, *, enabled: bool) -> None:
        """Enable or disable silent mode."""
        with _translate_errors():
            await self._client.set_silent_mode(device_name, enabled)

    async def async_set_child_lock(self, device_name: str, *, enabled: bool) -> None:
        """Enable or disable the child lock."""
        with _translate_errors():
            await self._client.set_child_lock(device_name, enabled)

    def watch_status(
        self,
        *,
        ca_certs: str | None = None,
        tls_insecure: bool = False,
    ) -> StatusStream:
        """Return a fresh MQTT status stream (caller starts/stops it)."""
        return self._client.watch_status(ca_certs=ca_certs, tls_insecure=tls_insecure)
