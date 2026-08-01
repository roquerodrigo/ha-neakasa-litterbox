"""
Device registry identifiers for litter boxes and the cats linked to them.

Each cat is a device of its own, anchored ``via_device`` to the litter
box it belongs to, so both share one identifier namespace. Removing a
cat from the mobile app leaves its device behind in Home Assistant —
matching registry entries against what the cloud still reports is what
tells the two apart.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .data import NeakasaPayload


def cat_identifier(iot_id: str, cat_id: int) -> str:
    """Return the device registry identifier of a cat on a litter box."""
    return f"{iot_id}-cat-{cat_id}"


def live_identifiers(payload: NeakasaPayload | None) -> frozenset[str]:
    """Return every identifier the cloud still reports, litter boxes and cats."""
    if payload is None:
        return frozenset()
    return frozenset(
        identifier
        for iot_id, snapshot in payload.devices.items()
        for identifier in (
            iot_id,
            *(cat_identifier(iot_id, cat.id) for cat in snapshot.cats),
        )
    )
