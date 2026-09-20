"""Capteurs horodatés : prochain réveil, début de progression, dernier réveil."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ReveilEntity
from .manager import ReveilConfigEntry, ReveilManager


@dataclass(frozen=True, kw_only=True)
class ReveilSensorDescription(SensorEntityDescription):
    value_fn: Callable[[ReveilManager], datetime | None]


SENSORS: tuple[ReveilSensorDescription, ...] = (
    ReveilSensorDescription(
        key="next_alarm",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda m: m.next_ring,
    ),
    ReveilSensorDescription(
        key="pre_ring_start",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda m: m.pre_ring_start,
    ),
    ReveilSensorDescription(
        key="last_dismissed",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda m: m.last_dismissed,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ReveilConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager = entry.runtime_data
    async_add_entities(ReveilSensor(manager, desc) for desc in SENSORS)


class ReveilSensor(ReveilEntity, SensorEntity):
    entity_description: ReveilSensorDescription

    def __init__(self, manager: ReveilManager, description: ReveilSensorDescription) -> None:
        super().__init__(manager, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> datetime | None:
        return self.entity_description.value_fn(self._manager)
