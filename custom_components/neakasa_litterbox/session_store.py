"""Keeps the cloud session across restarts, so setup can skip the sign-in."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from homeassistant.helpers.storage import Store
from neakasa_litterbox_sdk import LoginResult

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import JsonObject, NeakasaStoredSession


_STORAGE_VERSION = 1
_SAVE_DELAY_SECONDS = 1


class NeakasaSessionStore:
    """
    Persists the session the cloud issued to the account of a config entry.

    Signing in takes several seconds, most of it in the four step IoT
    handshake. A restored session costs nothing; when the cloud rejects it,
    the SDK mints a new IoT token and the coordinator signs in again, the
    same recovery a session dropped mid run already gets. Only complete
    sessions are kept, and only for the account and region that created
    them, so changing the credentials never reuses another account's session.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        *,
        username: str,
        region: str,
    ) -> None:
        """Bind the store to the storage file of a config entry."""
        self._store: Store[NeakasaStoredSession] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}.session",
            private=True,
        )
        self._username = username
        self._region = region
        self._session: LoginResult | None = None

    async def async_load(self) -> LoginResult | None:
        """Return the saved session, or ``None`` when there is no usable one."""
        stored = await self._store.async_load()
        if (
            stored is None
            or stored["username"] != self._username
            or stored["region"] != self._region
        ):
            return None
        session = LoginResult.from_dict(stored["login"])
        if not session.iot_token:
            return None
        LOGGER.debug("Restored the cloud session saved by a previous run")
        self._session = session
        return session

    def async_schedule_save(self, session: LoginResult | None) -> None:
        """Save ``session`` shortly when it differs from the one already kept."""
        if session is None or session is self._session or not session.iot_token:
            return
        self._session = session
        stored = self._stored_session(session)
        self._store.async_delay_save(lambda: stored, _SAVE_DELAY_SECONDS)

    async def async_save(self) -> None:
        """Write the kept session now, so a reload cannot read an outdated one."""
        if self._session is not None:
            await self._store.async_save(self._stored_session(self._session))

    async def async_remove(self) -> None:
        """Delete the storage file."""
        await self._store.async_remove()

    def _stored_session(self, session: LoginResult) -> NeakasaStoredSession:
        """Return ``session`` in its persisted shape."""
        return {
            "username": self._username,
            "region": self._region,
            "login": cast("JsonObject", session.to_dict()),
        }
