"""Shape of the cloud session persisted between runs."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from .json_types import JsonObject


class NeakasaStoredSession(TypedDict):
    """Cloud session saved for the account and region that created it."""

    username: str
    region: str
    login: JsonObject
