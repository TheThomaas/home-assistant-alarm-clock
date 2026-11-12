"""Intégration Réveil : planificateur d'événements de réveil."""

from __future__ import annotations

import voluptuous as vol
from pathlib import Path

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import ATTR_DEVICE_ID, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import (
    config_validation as cv,
    entity_registry as er,
    device_registry as dr,
)
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED

from .const import (
    ATTR_DAY,
    ATTR_DAYS,
    ATTR_TIME,
    DATA_CARD_PATH_REGISTERED,
    DAYS,
    DOMAIN,
    PLATFORMS,
    SERVICE_DISMISS,
    SERVICE_SET_DAYS,
    SERVICE_SET_TIME,
    STORAGE_VERSION,
)
from .manager import ReveilConfigEntry, ReveilManager

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_TARGET_FIELDS = {
    vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
}

SET_TIME_SCHEMA = vol.Schema(
    {
        **_TARGET_FIELDS,
        vol.Optional(ATTR_DAY): vol.In(DAYS),
        vol.Optional(ATTR_TIME): cv.time,
    },
    extra=vol.ALLOW_EXTRA,
)
SET_DAYS_SCHEMA = vol.Schema(
    {
        **_TARGET_FIELDS,
        vol.Required(ATTR_DAYS): vol.All(cv.ensure_list, [vol.In(DAYS)]),
    },
    extra=vol.ALLOW_EXTRA,
)
DISMISS_SCHEMA = vol.Schema(_TARGET_FIELDS, extra=vol.ALLOW_EXTRA)


def _resolve_managers(hass: HomeAssistant, call: ServiceCall) -> list[ReveilManager]:
    """Retrouve les réveils ciblés (par appareil ou par entité)."""
    device_ids: set[str] = set(call.data.get(ATTR_DEVICE_ID, []))

    ent_reg = er.async_get(hass)
    for entity_id in call.data.get(ATTR_ENTITY_ID, []):
        entity = ent_reg.async_get(entity_id)
        if entity is None or entity.device_id is None:
            raise ServiceValidationError(f"L'entité {entity_id} n'appartient à aucun réveil")
        device_ids.add(entity.device_id)

    if not device_ids:
        raise ServiceValidationError("Cible manquante : indiquez un appareil ou une entité Réveil")

    dev_reg = dr.async_get(hass)
    managers: list[ReveilManager] = []
    for device_id in device_ids:
        device = dev_reg.async_get(device_id)
        if device is None:
            raise ServiceValidationError(f"Appareil inconnu : {device_id}")
        for entry_id in device.config_entries:
            entry = hass.config_entries.async_get_entry(entry_id)
            if (
                entry is not None
                and entry.domain == DOMAIN
                and entry.state is ConfigEntryState.LOADED
            ):
                managers.append(entry.runtime_data)

    if not managers:
        raise ServiceValidationError("Aucun réveil actif trouvé pour cette cible")
    return managers


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Enregistre les services (une seule fois pour tous les réveils)."""

    async def _register_card_resource(event):
        lovelace = hass.data.get("lovelace")
        if not lovelace or not hasattr(lovelace, "resources"):
            _LOGGER.warning(
                "Lovelace resources indisponibles, carte non enregistrée"
            )
            return
        
        resources = lovelace.resources
        card_url = f"/api/{DOMAIN}/reveil-card.js"
        
        existing = [r for r in resources.async_items() 
                   if r.get("url", "").startswith(card_url)]
        
        if not existing:
            await resources.async_create_item({
                "url": card_url,
                "res_type": "module",
            })
    
    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STARTED, _register_card_resource
    )

    async def handle_set_time(call: ServiceCall) -> None:
        day = call.data.get(ATTR_DAY)
        value = call.data.get(ATTR_TIME)
        if day is None and value is None:
            raise ServiceValidationError(
                "Indiquez une heure (et éventuellement un jour), "
                "ou un jour seul pour effacer sa surcharge"
            )
        for manager in _resolve_managers(hass, call):
            await manager.async_set_time(day, value)

    async def handle_set_days(call: ServiceCall) -> None:
        for manager in _resolve_managers(hass, call):
            await manager.async_set_days(call.data[ATTR_DAYS])

    async def handle_dismiss(call: ServiceCall) -> None:
        for manager in _resolve_managers(hass, call):
            await manager.async_dismiss()

    hass.services.async_register(DOMAIN, SERVICE_SET_TIME, handle_set_time, schema=SET_TIME_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_DAYS, handle_set_days, schema=SET_DAYS_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_DISMISS, handle_dismiss, schema=DISMISS_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ReveilConfigEntry) -> bool:
    """Crée un réveil à partir d'une config entry."""
    manager = ReveilManager(hass, entry)
    await manager.async_load()
    entry.runtime_data = manager

    manager.async_start()
    entry.async_on_unload(manager.async_stop)

    # Le chemin statique de la carte est global au domaine : il doit être
    # enregistré une seule fois par instance de Home Assistant. S'appuyer sur
    # la taille de hass.data[DOMAIN] ne marchait pas (le dict n'y était jamais
    # alimenté, donc la condition restait fausse et la carte répondait 404),
    # et un compteur d'entrées repasserait à 1 après un unload — aiohttp
    # refuse alors la seconde déclaration de la route.
    if not hass.data.get(DATA_CARD_PATH_REGISTERED):
        www_path = Path(__file__).parent / "www"
        card_file = www_path / "reveil-card.js"

        await hass.http.async_register_static_paths([
            StaticPathConfig(f"/api/{DOMAIN}/reveil-card.js", str(card_file), cache_headers=False)
        ])
        hass.data[DATA_CARD_PATH_REGISTERED] = True

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_update))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ReveilConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Supprime l'état persistant du réveil."""
    await Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}").async_remove()


async def _async_reload_on_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recharge le réveil quand ses options changent (durée de progression)."""
    await hass.config_entries.async_reload(entry.entry_id)
