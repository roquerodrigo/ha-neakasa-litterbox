"""Sensor platform for integration_blueprint."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity

from .entity import IntegrationBlueprintEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import IntegrationBlueprintConfigEntry, IntegrationBlueprintPost


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: IntegrationBlueprintConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        [IntegrationBlueprintTitleSensor(coordinator=entry.runtime_data.coordinator)],
    )


class IntegrationBlueprintTitleSensor(IntegrationBlueprintEntity, SensorEntity):
    """Sensor exposing the latest post title returned by the API."""

    _attr_translation_key = "title"
    _attr_icon = "mdi:format-quote-close"

    @property
    def unique_id(self) -> str:
        """Return a unique id derived from the config entry id."""
        return f"{self.coordinator.config_entry.entry_id}_title"

    @property
    def native_value(self) -> str | None:
        """
        Return the title from the latest fetched post, if any.

        ``coordinator.data`` is typed as the post payload because that's the
        coordinator's TypeVar binding, but at runtime it can still be ``None``
        before the first successful refresh.
        """
        data: IntegrationBlueprintPost | None = self.coordinator.data
        if data is None:
            return None
        return data["title"]
