from __future__ import annotations

import dataclasses

import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.neakasa_litterbox.const import DOMAIN
from custom_components.neakasa_litterbox.session_store import NeakasaSessionStore

_ENTRY_ID = "entry"
_STORAGE_KEY = f"{DOMAIN}.{_ENTRY_ID}.session"


def _store(hass, username="user@example.com", region="us") -> NeakasaSessionStore:
    return NeakasaSessionStore(hass, _ENTRY_ID, username=username, region=region)


def _stored(hass_storage, session, username="user@example.com", region="us"):
    hass_storage[_STORAGE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": _STORAGE_KEY,
        "data": {
            "username": username,
            "region": region,
            "login": session.to_dict(),
        },
    }


async def _let_delayed_save_run(hass, freezer):
    freezer.tick(2)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_load_without_file_returns_none(hass, hass_storage):
    assert await _store(hass).async_load() is None


async def test_saved_session_round_trips(hass, hass_storage, sample_session):
    store = _store(hass)
    store.async_schedule_save(sample_session)
    await store.async_save()

    assert await _store(hass).async_load() == sample_session


@pytest.mark.parametrize(
    ("username", "region"),
    [("other@example.com", "us"), ("user@example.com", "eu")],
)
async def test_session_of_other_account_or_region_is_ignored(
    hass, hass_storage, sample_session, username, region
):
    _stored(hass_storage, sample_session, username=username, region=region)
    assert await _store(hass).async_load() is None


async def test_session_without_iot_token_is_ignored(hass, hass_storage, sample_session):
    _stored(hass_storage, dataclasses.replace(sample_session, iot_token=""))
    assert await _store(hass).async_load() is None


async def test_schedule_save_writes_after_delay(
    hass, hass_storage, sample_session, freezer
):
    store = _store(hass)
    store.async_schedule_save(sample_session)
    assert _STORAGE_KEY not in hass_storage

    await _let_delayed_save_run(hass, freezer)

    assert hass_storage[_STORAGE_KEY]["data"]["login"] == sample_session.to_dict()


@pytest.mark.parametrize(
    "session_factory",
    [
        lambda _session: None,
        lambda session: dataclasses.replace(session, iot_token=""),
    ],
)
async def test_incomplete_session_is_not_saved(
    hass, hass_storage, sample_session, session_factory
):
    store = _store(hass)
    store.async_schedule_save(session_factory(sample_session))
    await store.async_save()
    assert _STORAGE_KEY not in hass_storage


async def test_restored_session_is_not_written_again(
    hass, hass_storage, sample_session, freezer
):
    _stored(hass_storage, sample_session)
    store = _store(hass)
    restored = await store.async_load()
    hass_storage.pop(_STORAGE_KEY)

    store.async_schedule_save(restored)
    await _let_delayed_save_run(hass, freezer)

    assert _STORAGE_KEY not in hass_storage


async def test_newer_session_replaces_the_saved_one(hass, hass_storage, sample_session):
    store = _store(hass)
    store.async_schedule_save(sample_session)
    newer = dataclasses.replace(sample_session, iot_token="newer")
    store.async_schedule_save(newer)
    await store.async_save()
    assert hass_storage[_STORAGE_KEY]["data"]["login"]["iot_token"] == "newer"


async def test_remove_deletes_the_file(hass, hass_storage, sample_session):
    store = _store(hass)
    store.async_schedule_save(sample_session)
    await store.async_save()
    await store.async_remove()
    assert _STORAGE_KEY not in hass_storage
