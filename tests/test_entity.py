from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.neakasa_litterbox.const import DOMAIN, MANUFACTURER
from custom_components.neakasa_litterbox.data import (
    NeakasaDeviceSnapshot,
    NeakasaPayload,
)
from custom_components.neakasa_litterbox.entity import (
    NeakasaCatEntity,
    NeakasaDeviceEntity,
)


def _payload(snap: NeakasaDeviceSnapshot) -> NeakasaPayload:
    return NeakasaPayload(devices={snap.device["iot_id"]: snap})


def _snapshot(sample_device, sample_status, sample_cat) -> NeakasaDeviceSnapshot:
    return NeakasaDeviceSnapshot(
        device={
            "iot_id": sample_device.iot_id,
            "device_name": sample_device.device_name,
            "product_name": sample_device.product_name,
            "firmware_version": sample_status.firmware_version,
            "hardware_version": sample_status.hardware_version,
        },
        status=sample_status,
        cats=(sample_cat,),
        visits_today=0,
        last_visit_at=None,
        cat_stats={},
    )


def _device_entity(sample_device, sample_status, sample_cat) -> NeakasaDeviceEntity:
    coordinator = MagicMock()
    coordinator.data = _payload(_snapshot(sample_device, sample_status, sample_cat))
    coordinator.last_update_success = True
    return NeakasaDeviceEntity(coordinator=coordinator, iot_id=sample_device.iot_id)


def _cat_entity(sample_device, sample_status, sample_cat) -> NeakasaCatEntity:
    coordinator = MagicMock()
    coordinator.data = _payload(_snapshot(sample_device, sample_status, sample_cat))
    coordinator.last_update_success = True
    return NeakasaCatEntity(
        coordinator=coordinator,
        iot_id=sample_device.iot_id,
        cat_id=sample_cat.id,
    )


def test_device_entity_iot_id(sample_device, sample_status, sample_cat):
    entity = _device_entity(sample_device, sample_status, sample_cat)
    assert entity.iot_id == sample_device.iot_id


def test_device_entity_snapshot(sample_device, sample_status, sample_cat):
    entity = _device_entity(sample_device, sample_status, sample_cat)
    snap = entity.snapshot
    assert snap is not None
    assert snap.status is sample_status


def test_device_entity_device_info_identifiers(
    sample_device, sample_status, sample_cat
):
    entity = _device_entity(sample_device, sample_status, sample_cat)
    info = entity.device_info
    assert (DOMAIN, sample_device.iot_id) in info["identifiers"]
    assert info["manufacturer"] == MANUFACTURER


def test_device_entity_device_info_versions(sample_device, sample_status, sample_cat):
    entity = _device_entity(sample_device, sample_status, sample_cat)
    info = entity.device_info
    assert info["sw_version"] == sample_status.firmware_version
    assert info["hw_version"] == sample_status.hardware_version


def test_device_entity_snapshot_returns_none_without_data(sample_device):
    coordinator = MagicMock()
    coordinator.data = None
    coordinator.last_update_success = True
    entity = NeakasaDeviceEntity(coordinator=coordinator, iot_id=sample_device.iot_id)
    assert entity.snapshot is None
    assert entity.available is False


def test_device_entity_device_info_without_snapshot(sample_device):
    coordinator = MagicMock()
    coordinator.data = None
    coordinator.last_update_success = True
    entity = NeakasaDeviceEntity(coordinator=coordinator, iot_id=sample_device.iot_id)
    info = entity.device_info
    assert info["name"] == sample_device.iot_id


def test_cat_entity_resolves_cat(sample_device, sample_status, sample_cat):
    entity = _cat_entity(sample_device, sample_status, sample_cat)
    assert entity.cat is sample_cat
    assert entity.iot_id == sample_device.iot_id
    assert entity.cat_id == sample_cat.id
    assert entity.available is True


def _cat_entity_in_hass(hass, sample_device, sample_status, sample_cat):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    entity = _cat_entity(sample_device, sample_status, sample_cat)
    entity.coordinator.config_entry.entry_id = entry.entry_id
    entity.hass = hass
    return entity, entry


async def test_cat_entity_device_info_links_to_litter_box(
    hass, sample_device, sample_status, sample_cat
):
    entity, entry = _cat_entity_in_hass(hass, sample_device, sample_status, sample_cat)
    litter_box = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, sample_device.iot_id)},
    )
    info = entity.device_info
    assert info["via_device_id"] == litter_box.id
    assert "via_device" not in info


async def test_cat_entity_device_info_without_registered_litter_box(
    hass, sample_device, sample_status, sample_cat
):
    entity, _ = _cat_entity_in_hass(hass, sample_device, sample_status, sample_cat)
    assert "via_device_id" not in entity.device_info


def test_cat_entity_unavailable_without_payload(sample_device, sample_cat):
    coordinator = MagicMock()
    coordinator.data = None
    coordinator.last_update_success = True
    entity = NeakasaCatEntity(
        coordinator=coordinator,
        iot_id=sample_device.iot_id,
        cat_id=sample_cat.id,
    )
    assert entity.cat is None
    assert entity.available is False


def test_cat_entity_unavailable_when_device_dropped(sample_device, sample_cat):
    coordinator = MagicMock()
    coordinator.data = NeakasaPayload(devices={})
    coordinator.last_update_success = True
    entity = NeakasaCatEntity(
        coordinator=coordinator,
        iot_id=sample_device.iot_id,
        cat_id=sample_cat.id,
    )
    assert entity.cat is None


async def test_cat_entity_device_info_falls_back_to_id(hass, sample_device, sample_cat):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    coordinator = MagicMock()
    coordinator.data = None
    coordinator.last_update_success = True
    coordinator.config_entry.entry_id = entry.entry_id
    entity = NeakasaCatEntity(
        coordinator=coordinator,
        iot_id=sample_device.iot_id,
        cat_id=sample_cat.id,
    )
    entity.hass = hass
    info = entity.device_info
    assert info["name"] == str(sample_cat.id)
