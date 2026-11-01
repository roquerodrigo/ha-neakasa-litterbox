from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx
import pytest
import respx
from homeassistant.components.image import async_get_image
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.neakasa_litterbox.const import DOMAIN
from custom_components.neakasa_litterbox.data import NeakasaPayload

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory

ENTITY_ID = "image.neakasa_m1_whiskers_photo"
PHOTO_URL = "https://photos.example.com/cat.png?signature=first"
RESIGNED_PHOTO_URL = "https://photos.example.com/cat.png?signature=second"
REPLACED_PHOTO_URL = "https://photos.example.com/new.png?signature=third"
PHOTO_PATH = "user/1/catbox/box/1.png"
REPLACED_PHOTO_PATH = "user/1/catbox/box/2.png"


def _publish(entry, **cat_changes) -> None:
    coordinator = entry.runtime_data.coordinator
    coordinator.async_set_updated_data(
        NeakasaPayload(
            devices={
                iot_id: dataclasses.replace(
                    snapshot,
                    cats=tuple(
                        dataclasses.replace(cat, **cat_changes) for cat in snapshot.cats
                    ),
                )
                for iot_id, snapshot in coordinator.data.devices.items()
            }
        )
    )


@pytest.fixture
async def photo_entry(hass, setup_integration):
    _publish(setup_integration, avatar=PHOTO_URL, path=PHOTO_PATH)
    await hass.async_block_till_done()
    return setup_integration


async def test_cat_without_photo_is_unknown(hass, setup_integration):
    assert hass.states.get(ENTITY_ID).state == "unknown"
    with pytest.raises(HomeAssistantError):
        await async_get_image(hass, ENTITY_ID)


async def test_serves_the_photo_with_its_content_type(hass, photo_entry):
    with respx.mock:
        respx.get(PHOTO_URL).mock(
            return_value=httpx.Response(
                200, content=b"first", headers={"content-type": "image/png"}
            )
        )
        image = await async_get_image(hass, ENTITY_ID)
    assert image.content == b"first"
    assert image.content_type == "image/png"


async def test_signed_url_is_not_exposed(hass, photo_entry):
    state = hass.states.get(ENTITY_ID)
    assert "signature" not in str(state.attributes)
    assert "signature" not in state.state


async def test_new_signature_of_the_same_photo_changes_nothing(
    hass, photo_entry, freezer: FrozenDateTimeFactory
):
    before = hass.states.get(ENTITY_ID).state
    with respx.mock:
        route = respx.get(PHOTO_URL).mock(
            return_value=httpx.Response(
                200, content=b"first", headers={"content-type": "image/png"}
            )
        )
        await async_get_image(hass, ENTITY_ID)
        freezer.move_to(datetime(2030, 1, 1, tzinfo=UTC))
        _publish(photo_entry, avatar=RESIGNED_PHOTO_URL)
        await hass.async_block_till_done()
        image = await async_get_image(hass, ENTITY_ID)
    assert hass.states.get(ENTITY_ID).state == before
    assert image.content == b"first"
    assert route.call_count == 1


async def test_replaced_photo_is_downloaded_again(
    hass, photo_entry, freezer: FrozenDateTimeFactory
):
    before = hass.states.get(ENTITY_ID).state
    with respx.mock:
        respx.get(PHOTO_URL).mock(
            return_value=httpx.Response(
                200, content=b"first", headers={"content-type": "image/png"}
            )
        )
        respx.get(REPLACED_PHOTO_URL).mock(
            return_value=httpx.Response(
                200, content=b"second", headers={"content-type": "image/png"}
            )
        )
        await async_get_image(hass, ENTITY_ID)
        freezer.move_to(datetime(2030, 1, 1, tzinfo=UTC))
        _publish(photo_entry, avatar=REPLACED_PHOTO_URL, path=REPLACED_PHOTO_PATH)
        await hass.async_block_till_done()
        image = await async_get_image(hass, ENTITY_ID)
    assert hass.states.get(ENTITY_ID).state != before
    assert image.content == b"second"


async def test_removed_photo_becomes_unknown(hass, photo_entry):
    _publish(photo_entry, avatar="", path="")
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "unknown"


async def test_failed_download_is_retried_on_the_next_request(hass, photo_entry):
    with respx.mock:
        route = respx.get(PHOTO_URL).mock(
            side_effect=[
                httpx.Response(403),
                httpx.Response(
                    200, content=b"first", headers={"content-type": "image/png"}
                ),
            ]
        )
        with pytest.raises(HomeAssistantError):
            await async_get_image(hass, ENTITY_ID)
        image = await async_get_image(hass, ENTITY_ID)
    assert image.content == b"first"
    assert route.call_count == 2


async def test_cat_dropped_by_the_cloud_is_unavailable(hass, photo_entry):
    coordinator = photo_entry.runtime_data.coordinator
    coordinator.async_set_updated_data(
        NeakasaPayload(
            devices={
                iot_id: dataclasses.replace(snapshot, cats=())
                for iot_id, snapshot in coordinator.data.devices.items()
            }
        )
    )
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "unavailable"


async def test_platform_registers_photo_on_the_cat_device(
    hass, setup_integration, sample_device, sample_cat
):
    entity = er.async_get(hass).async_get(ENTITY_ID)
    device = dr.async_get(hass).async_get_child_device_by_identifier(
        (DOMAIN, f"{sample_device.iot_id}-cat-{sample_cat.id}"),
        setup_integration.entry_id,
    )
    assert entity.unique_id == f"{sample_device.iot_id}_cat_{sample_cat.id}_photo"
    assert entity.device_id == device.id
