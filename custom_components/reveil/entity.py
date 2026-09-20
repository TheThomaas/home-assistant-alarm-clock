"""Entité de base partagée par toutes les plateformes."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .manager import ReveilManager


class ReveilEntity(Entity):
    """Entité rattachée à un réveil (un appareil par réveil)."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: ReveilManager, key: str) -> None:
        self._manager = manager
        self._attr_translation_key = key
        self._attr_unique_id = f"{manager.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, manager.entry.entry_id)},
            name=manager.entry.title,
            manufacturer="Réveil",
            model="Réveil programmable",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self._manager.async_add_listener(self.async_write_ha_state)
        )
