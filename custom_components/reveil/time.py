"""Heure par défaut et heures par jour."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DAYS
from .entity import ReveilEntity
from .manager import ReveilConfigEntry, ReveilManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ReveilConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager = entry.runtime_data
    async_add_entities(
        [ReveilTime(manager, None), *(ReveilTime(manager, day) for day in DAYS)]
    )


class ReveilTime(ReveilEntity, TimeEntity):
    """Heure par défaut (day=None) ou surcharge d'un jour (vide = heure par défaut)."""

    def __init__(self, manager: ReveilManager, day: str | None) -> None:
        super().__init__(manager, "default_time" if day is None else f"time_{day}")
        self._day = day

    @property
    def native_value(self) -> time | None:
        return self._manager.get_time(self._day)

    async def async_set_value(self, value: time) -> None:
        await self._manager.async_set_time(self._day, value)
