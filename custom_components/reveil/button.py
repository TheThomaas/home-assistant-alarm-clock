"""Bouton « Je suis réveillé » (équivalent du service reveil.dismiss)."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import ReveilEntity
from .manager import ReveilConfigEntry, ReveilManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ReveilConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([ReveilDismissButton(entry.runtime_data)])


class ReveilDismissButton(ReveilEntity, ButtonEntity):
    def __init__(self, manager: ReveilManager) -> None:
        super().__init__(manager, "dismiss")

    async def async_press(self) -> None:
        await self._manager.async_dismiss()
