"""Constantes de l'intégration Réveil."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "reveil"

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
]

# Index 0 = lundi, comme datetime.weekday()
DAYS: tuple[str, ...] = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
DEFAULT_ACTIVE_DAYS: tuple[str, ...] = DAYS[:5]

CONF_DEFAULT_TIME = "default_time"
CONF_LEAD_MINUTES = "lead_minutes"
DEFAULT_TIME = "07:00:00"
DEFAULT_LEAD_MINUTES = 20

EVENT_PRE_RING = "reveil_pre_ring"
EVENT_RING = "reveil_ring"
EVENT_DISMISSED = "reveil_dismissed"

SERVICE_SET_TIME = "set_time"
SERVICE_SET_DAYS = "set_days"
SERVICE_DISMISS = "dismiss"

ATTR_DAY = "day"
ATTR_DAYS = "days"
ATTR_TIME = "time"

# Clé hass.data marquant l'enregistrement (unique) du chemin statique de la carte.
DATA_CARD_PATH_REGISTERED = "card_path_registered"

STORAGE_VERSION = 1

# Un « dismiss » est rattaché à la dernière sonnerie si elle date de moins de 6 h
DISMISS_WINDOW_SECONDS = 6 * 3600
