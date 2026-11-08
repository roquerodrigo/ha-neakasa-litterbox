"""Neakasa Litterbox API client (wraps the neakasa-litterbox-sdk)."""

from __future__ import annotations

import contextlib
from contextlib import contextmanager
from typing import TYPE_CHECKING, Literal

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
    NeakasaApiClientDeviceBusyError,
    NeakasaApiClientError,
    NeakasaApiClientSessionExpiredError,
)

# The cloud rejects a property readback with this code while the box is
# mid-cycle (cleaning/restoring/leveling). It's expected and transient,
# so it gets its own error type the coordinator can keep-last on.
_DEVICE_BUSY_CODE = 29003

# The account listing also returns other Neakasa/Neabot products (e.g. robot
# vacuums); the catbox endpoints reject them, so only this category is kept.
_LITTER_BOX_CATEGORY_KEY = "CatLitter"

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from neakasa_litterbox_sdk import (
        Cat,
        Device,
        DeviceStatus,
        LoginResult,
        StatusStream,
        ToiletRecord,
    )


@contextmanager
def _translate_errors() -> Iterator[None]:
    """Map SDK exceptions to the integration's hierarchy."""
    try:
        yield
    except SessionExpiredError as exc:
        raise NeakasaApiClientSessionExpiredError(str(exc)) from exc
    except (InvalidCredentialsError, AuthenticationError) as exc:
        raise NeakasaApiClientAuthenticationError(str(exc)) from exc
    except TransportError as exc:
        raise NeakasaApiClientCommunicationError(str(exc)) from exc
    except ApiError as exc:
        if exc.code == _DEVICE_BUSY_CODE:
            raise NeakasaApiClientDeviceBusyError(str(exc)) from exc
        raise NeakasaApiClientError(str(exc)) from exc
    except NeakasaError as exc:
        raise NeakasaApiClientError(str(exc)) from exc


class NeakasaApiClient:
    """Async client for the Neakasa cloud, wrapping the SDK NeakasaClient."""

    def __init__(
        self,
        username: str,
        password: str,
        region: str,
        timeout: float = 10.0,
        session_listener: Callable[[LoginResult | None], None] | None = None,
    ) -> None:
        """
        Build a client bound to ``region`` (US/EU/AP).

        ``session_listener`` receives the session after every call, because
        the SDK replaces it on its own whenever the cloud rejects a token.
        """
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
        self._session_listener = session_listener

    @property
    def sdk(self) -> NeakasaClient:
        """Expose the underlying SDK client (read-only)."""
        return self._client

    async def async_login(self, cached: LoginResult | None = None) -> None:
        """Resume the ``cached`` session, or sign in afresh without one."""
        with self._calling_cloud():
            await self._client.login(cached=cached)

    @contextmanager
    def _calling_cloud(self) -> Iterator[None]:
        """Translate SDK errors and report the session the call left behind."""
        try:
            with _translate_errors():
                yield
        finally:
            if self._session_listener is not None:
                self._session_listener(self._client.login_result)

    async def async_close(self) -> None:
        """Tear down the underlying session, swallowing SDK errors."""
        with contextlib.suppress(NeakasaError):
            await self._client.close()

    async def async_list_devices(self) -> list[Device]:
        """Return every litter box bound to the authenticated account."""
        with self._calling_cloud():
            devices = await self._client.list_devices()
        return [
            device
            for device in devices
            if device.category_key == _LITTER_BOX_CATEGORY_KEY
        ]

    async def async_get_status(self, device_name: str) -> DeviceStatus:
        """Return the live status snapshot for a device."""
        with self._calling_cloud():
            return await self._client.get_status(device_name)

    async def async_list_cats(self, device_name: str) -> list[Cat]:
        """Return the cat profiles attached to a device."""
        with self._calling_cloud():
            return await self._client.list_cats(device_name)

    async def async_set_cat_weight(
        self,
        device_name: str,
        cat_id: int,
        weight: float,
        *,
        unit: Literal["kg", "lb"],
        zone_seconds: int,
    ) -> None:
        """Save ``weight`` to a cat's profile, leaving its other fields intact."""
        with self._calling_cloud():
            await self._client.set_cat_weight(
                device_name,
                cat_id,
                weight,
                unit=unit,
                zone_seconds=zone_seconds,
            )

    async def async_get_toilet_records(
        self,
        device_name: str,
        start_time: int,
        end_time: int,
    ) -> list[ToiletRecord]:
        """Return raw toilet records in the given epoch-seconds window."""
        with self._calling_cloud():
            return await self._client.get_toilet_records(
                device_name, start_time, end_time
            )

    async def async_start_clean(self, device_name: str) -> None:
        """Trigger a manual clean cycle."""
        with self._calling_cloud():
            await self._client.start_clean(device_name)

    async def async_stop_clean(self, device_name: str) -> None:
        """Abort a running clean cycle."""
        with self._calling_cloud():
            await self._client.stop_clean(device_name)

    async def async_start_level(self, device_name: str) -> None:
        """Trigger a manual sand-level operation."""
        with self._calling_cloud():
            await self._client.start_level(device_name)

    async def async_stop_level(self, device_name: str) -> None:
        """Abort a running sand-level operation."""
        with self._calling_cloud():
            await self._client.stop_level(device_name)

    async def async_calibrate_sand(self, device_name: str, percent: int) -> None:
        """Calibrate the sand sensor to ``percent`` (0-100)."""
        with self._calling_cloud():
            await self._client.calibrate_sand(device_name, percent)

    async def async_set_auto_clean(self, device_name: str, *, enabled: bool) -> None:
        """Enable or disable automatic cleaning."""
        with self._calling_cloud():
            await self._client.set_auto_clean(device_name, enabled)

    async def async_set_auto_level(self, device_name: str, *, enabled: bool) -> None:
        """Enable or disable automatic levelling."""
        with self._calling_cloud():
            await self._client.set_auto_level(device_name, enabled)

    async def async_set_silent_mode(self, device_name: str, *, enabled: bool) -> None:
        """Enable or disable silent mode."""
        with self._calling_cloud():
            await self._client.set_silent_mode(device_name, enabled)

    async def async_set_child_lock(self, device_name: str, *, enabled: bool) -> None:
        """Enable or disable the child lock."""
        with self._calling_cloud():
            await self._client.set_child_lock(device_name, enabled)

    def watch_status(self) -> StatusStream:
        """Return a fresh MQTT status stream (caller starts/stops it)."""
        return self._client.watch_status()
