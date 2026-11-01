from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeassistant.const import EVENT_STATE_CHANGED, STATE_UNKNOWN
from homeassistant.helpers import entity_registry as er
from neakasa_litterbox_sdk import RecordType, ToiletRecord
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)

from custom_components.neakasa_litterbox.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_FIRST_VISIT_ID = 1


def _record(
    record_id: int,
    record_type: RecordType = RecordType.CAT_VISIT,
    *,
    cat_id: int = 42,
    start_time: int = 1_700_001_000,
    end_time: int = 1_700_001_100,
) -> ToiletRecord:
    is_visit = record_type is RecordType.CAT_VISIT
    return ToiletRecord(
        record_id=record_id,
        record_type=record_type,
        cat_id=cat_id,
        start_time=start_time,
        end_time=end_time,
        weight=4.1 if is_visit else 0,
        unit="kg" if is_visit else "",
        way=0,
    )


def _entity_id(hass: HomeAssistant, sample_device) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        "event", DOMAIN, f"{sample_device.iot_id}_activity"
    )
    assert entity_id is not None
    return entity_id


async def _poll(hass, entry, mock_api_client, records: list[ToiletRecord]) -> None:
    mock_api_client.async_get_toilet_records.return_value = records
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()


def _fired_event_types(state_changes, entity_id: str) -> list[str]:
    return [
        event.data["new_state"].attributes["event_type"]
        for event in state_changes
        if event.data["entity_id"] == entity_id
    ]


async def test_first_setup_seeds_without_replaying_the_lookback_window(
    hass, setup_integration, sample_device
):
    state = hass.states.get(_entity_id(hass, sample_device))
    assert state.state == STATE_UNKNOWN
    assert state.attributes["event_type"] is None


async def test_event_types_are_declared(hass, setup_integration, sample_device):
    state = hass.states.get(_entity_id(hass, sample_device))
    assert state.attributes["event_types"] == [
        "cat_visit",
        "cleaning_completed",
        "leveling_completed",
    ]


async def test_new_visit_fires_with_the_time_it_happened(
    hass, setup_integration, mock_api_client, sample_device
):
    await _poll(hass, setup_integration, mock_api_client, [_record(2)])
    state = hass.states.get(_entity_id(hass, sample_device))
    assert state.attributes["event_type"] == "cat_visit"
    assert state.attributes["record_id"] == 2
    assert state.attributes["started_at"] == "2023-11-14T22:30:00+00:00"
    assert state.attributes["ended_at"] == "2023-11-14T22:31:40+00:00"
    assert state.attributes["duration_seconds"] == 100
    assert state.attributes["cat_id"] == 42
    assert state.attributes["cat_name"] == "Whiskers"
    assert state.attributes["weight"] == 4.1
    assert state.attributes["weight_unit"] == "kg"


async def test_unrecognized_cat_has_no_identity(
    hass, setup_integration, mock_api_client, sample_device
):
    await _poll(hass, setup_integration, mock_api_client, [_record(2, cat_id=0)])
    state = hass.states.get(_entity_id(hass, sample_device))
    assert state.attributes["cat_id"] is None
    assert state.attributes["cat_name"] is None


async def test_visit_of_a_cat_deleted_in_the_app_keeps_its_id(
    hass, setup_integration, mock_api_client, sample_device
):
    await _poll(hass, setup_integration, mock_api_client, [_record(2, cat_id=7)])
    state = hass.states.get(_entity_id(hass, sample_device))
    assert state.attributes["cat_id"] == 7
    assert state.attributes["cat_name"] is None


@pytest.mark.parametrize(
    ("record_type", "event_type"),
    [
        (RecordType.CLEAN_CYCLE, "cleaning_completed"),
        (RecordType.OTHER, "leveling_completed"),
    ],
)
async def test_machine_cycles_fire_without_cat_fields(
    hass, setup_integration, mock_api_client, sample_device, record_type, event_type
):
    record = _record(2, record_type, cat_id=0)
    await _poll(hass, setup_integration, mock_api_client, [record])
    state = hass.states.get(_entity_id(hass, sample_device))
    assert state.attributes["event_type"] == event_type
    assert state.attributes["duration_seconds"] == 100
    assert "cat_id" not in state.attributes
    assert "weight" not in state.attributes


async def test_each_record_of_a_poll_fires_once_oldest_first(
    hass, setup_integration, mock_api_client, sample_device
):
    state_changes = async_capture_events(hass, EVENT_STATE_CHANGED)
    records = [
        _record(5, end_time=1_700_002_000),
        _record(6, RecordType.CLEAN_CYCLE, end_time=1_700_001_500),
    ]
    await _poll(hass, setup_integration, mock_api_client, records)
    assert _fired_event_types(state_changes, _entity_id(hass, sample_device)) == [
        "cleaning_completed",
        "cat_visit",
    ]


async def test_record_seen_again_does_not_fire_twice(
    hass, setup_integration, mock_api_client, sample_device
):
    await _poll(hass, setup_integration, mock_api_client, [_record(2)])
    state_changes = async_capture_events(hass, EVENT_STATE_CHANGED)
    await _poll(hass, setup_integration, mock_api_client, [_record(2), _record(3)])
    assert _fired_event_types(state_changes, _entity_id(hass, sample_device)) == [
        "cat_visit"
    ]
    assert hass.states.get(_entity_id(hass, sample_device)).attributes["record_id"] == 3


async def test_reload_does_not_fire_reported_records_again(
    hass, setup_integration, mock_api_client, sample_device
):
    await _poll(hass, setup_integration, mock_api_client, [_record(2)])
    entity_id = _entity_id(hass, sample_device)
    triggered_at = hass.states.get(entity_id).state

    await hass.config_entries.async_reload(setup_integration.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == triggered_at
    assert state.attributes["record_id"] == 2


async def test_activity_during_downtime_fires_on_startup(
    hass, hass_storage, mock_api_client, enable_custom_integrations, sample_device
):
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="downtime",
        data={"username": "user@example.com", "password": "pass", "region": "us"},
        unique_id="user-example-com",
    )
    entry.add_to_hass(hass)
    hass_storage[f"{DOMAIN}.downtime.activity_records"] = {
        "version": 1,
        "minor_version": 1,
        "key": f"{DOMAIN}.downtime.activity_records",
        "data": {sample_device.iot_id: {"1": _FIRST_VISIT_ID}},
    }
    mock_api_client.async_get_toilet_records.return_value = [
        _record(_FIRST_VISIT_ID),
        _record(_FIRST_VISIT_ID + 1),
    ]

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(_entity_id(hass, sample_device))
    assert state.attributes["record_id"] == _FIRST_VISIT_ID + 1


async def test_removing_the_entry_deletes_the_storage_file(
    hass, hass_storage, setup_integration, mock_api_client
):
    await _poll(hass, setup_integration, mock_api_client, [_record(2)])
    storage_key = f"{DOMAIN}.{setup_integration.entry_id}.activity_records"
    await setup_integration.runtime_data.activity_record_tracker.async_save()
    assert storage_key in hass_storage

    await hass.config_entries.async_remove(setup_integration.entry_id)
    await hass.async_block_till_done()

    assert storage_key not in hass_storage
