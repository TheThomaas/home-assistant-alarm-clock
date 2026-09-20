"""Interrupteur global et un interrupteur par jour."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
        [ReveilSwitch(manager, None), *(ReveilSwitch(manager, day) for day in DAYS)]
    )


class ReveilSwitch(ReveilEntity, SwitchEntity):
    """Activation globale (day=None) ou activation d'un jour de la semaine."""

    def __init__(self, manager: ReveilManager, day: str | None) -> None:
        super().__init__(manager, "enabled" if day is None else f"day_{day}")
        self._day = day

    @property
    def is_on(self) -> bool:
        if self._day is None:
            return self._manager.enabled
        return self._manager.is_day_active(self._day)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)

    async def _set(self, value: bool) -> None:
        if self._day is None:
            await self._manager.async_set_enabled(value)
        else:
            await self._manager.async_set_day_active(self._day, value)
