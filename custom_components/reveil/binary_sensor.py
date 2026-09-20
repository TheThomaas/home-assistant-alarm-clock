"""Capteur binaire « sonne aujourd'hui »."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ReveilEntity
from .manager import ReveilConfigEntry, ReveilManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ReveilConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([ReveilRingsToday(entry.runtime_data)])


class ReveilRingsToday(ReveilEntity, BinarySensorEntity):
    """Actif si le réveil est activé aujourd'hui et pas encore confirmé."""

    def __init__(self, manager: ReveilManager) -> None:
        super().__init__(manager, "rings_today")

    @property
    def is_on(self) -> bool:
        return self._manager.rings_today
