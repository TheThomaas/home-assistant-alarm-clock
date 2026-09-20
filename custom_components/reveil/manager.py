"""Gestionnaire d'un réveil : état, planification et événements."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, time, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_time_change,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DEFAULT_TIME,
    CONF_LEAD_MINUTES,
    DAYS,
    DEFAULT_ACTIVE_DAYS,
    DEFAULT_LEAD_MINUTES,
    DEFAULT_TIME,
    DISMISS_WINDOW_SECONDS,
    DOMAIN,
    EVENT_DISMISSED,
    EVENT_PRE_RING,
    EVENT_RING,
    STORAGE_VERSION,
)
from .schedule import next_ring as compute_next_ring

_LOGGER = logging.getLogger(__name__)

type ReveilConfigEntry = ConfigEntry[ReveilManager]


def _parse_time(value: Any, default: time | None) -> time | None:
    """Convertit 'HH:MM[:SS]' en time, ou retourne `default`."""
    if isinstance(value, str):
        parsed = dt_util.parse_time(value)
        if parsed is not None:
            return parsed.replace(tzinfo=None, microsecond=0)
    return default


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, str):
        return dt_util.parse_datetime(value)
    return None


class ReveilManager:
    """État et planification d'un réveil (une config entry = un réveil)."""

    def __init__(self, hass: HomeAssistant, entry: ReveilConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )

        self._default_time: time = _parse_time(
            entry.data.get(CONF_DEFAULT_TIME), None
        ) or dt_util.parse_time(DEFAULT_TIME)  # type: ignore[assignment]
        self._day_times: dict[str, time | None] = dict.fromkeys(DAYS)
        self._days: dict[str, bool] = {d: d in DEFAULT_ACTIVE_DAYS for d in DAYS}
        self._enabled = True
        self._last_dismissed: datetime | None = None
        self._last_ring: datetime | None = None

        self._next_ring: datetime | None = None
        self._pre_fired_key: str | None = None
        self._unsub_timer: CALLBACK_TYPE | None = None
        self._unsub_midnight: CALLBACK_TYPE | None = None
        self._listeners: list[CALLBACK_TYPE] = []

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------
    async def async_load(self) -> None:
        """Charge l'état persistant."""
        stored = await self._store.async_load()
        if not stored:
            return
        self._default_time = _parse_time(stored.get("default_time"), self._default_time)  # type: ignore[assignment]
        day_times = stored.get("day_times") or {}
        days = stored.get("days") or {}
        for day in DAYS:
            self._day_times[day] = _parse_time(day_times.get(day), None)
            if day in days:
                self._days[day] = bool(days[day])
        self._enabled = bool(stored.get("enabled", True))
        self._last_dismissed = _parse_datetime(stored.get("last_dismissed"))
        self._last_ring = _parse_datetime(stored.get("last_ring"))

    @callback
    def async_start(self) -> None:
        """Démarre la planification."""
        self._schedule()
        self._unsub_midnight = async_track_time_change(
            self.hass, self._on_midnight, hour=0, minute=0, second=0
        )

    async def async_stop(self) -> None:
        """Arrête les timers et sauvegarde l'état."""
        self._cancel_timer()
        if self._unsub_midnight is not None:
            self._unsub_midnight()
            self._unsub_midnight = None
        await self._store.async_save(self._as_dict())

    # ------------------------------------------------------------------
    # Lecture de l'état
    # ------------------------------------------------------------------
    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def lead_minutes(self) -> int:
        return int(self.entry.options.get(CONF_LEAD_MINUTES, DEFAULT_LEAD_MINUTES))

    @property
    def next_ring(self) -> datetime | None:
        return self._next_ring

    @property
    def pre_ring_start(self) -> datetime | None:
        if self._next_ring is None or self.lead_minutes <= 0:
            return None
        return dt_util.as_utc(self._next_ring) - timedelta(minutes=self.lead_minutes)

    @property
    def last_dismissed(self) -> datetime | None:
        return self._last_dismissed

    @property
    def rings_today(self) -> bool:
        """Vrai si le réveil est actif aujourd'hui et pas encore confirmé."""
        today = dt_util.now().date()
        if not self._enabled or not self._days[DAYS[today.weekday()]]:
            return False
        if (
            self._last_dismissed is not None
            and dt_util.as_local(self._last_dismissed).date() == today
        ):
            return False
        return True

    def is_day_active(self, day: str) -> bool:
        return self._days[day]

    def get_time(self, day: str | None) -> time | None:
        """Heure par défaut (day=None) ou surcharge du jour (None si absente)."""
        return self._default_time if day is None else self._day_times[day]

    def effective_time(self, day: str) -> time:
        return self._day_times[day] or self._default_time

    # ------------------------------------------------------------------
    # Écoute des changements (entités)
    # ------------------------------------------------------------------
    @callback
    def async_add_listener(self, listener: CALLBACK_TYPE) -> CALLBACK_TYPE:
        self._listeners.append(listener)

        @callback
        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    @callback
    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    # ------------------------------------------------------------------
    # Modifications
    # ------------------------------------------------------------------
    async def async_set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self._changed()

    async def async_set_day_active(self, day: str, active: bool) -> None:
        self._days[day] = active
        self._changed()

    async def async_set_days(self, days: list[str]) -> None:
        """Active exactement les jours donnés, désactive les autres."""
        for day in DAYS:
            self._days[day] = day in days
        self._changed()

    async def async_set_time(self, day: str | None, value: time | None) -> None:
        """Définit l'heure par défaut (day=None) ou la surcharge d'un jour.

        value=None avec un jour efface la surcharge (retour à l'heure par défaut).
        """
        if value is not None:
            value = value.replace(second=0, microsecond=0, tzinfo=None)
        if day is None:
            if value is None:
                raise ValueError("L'heure par défaut ne peut pas être vide")
            self._default_time = value
        else:
            self._day_times[day] = value
        self._changed()

    async def async_dismiss(self) -> None:
        """Confirme le réveil : émet `reveil_dismissed`."""
        now = dt_util.now()
        ring_at = self._last_ring
        delay: int | None = None
        if ring_at is not None:
            delta = (now - ring_at).total_seconds()
            if 0 <= delta <= DISMISS_WINDOW_SECONDS:
                delay = int(delta)
            else:
                ring_at = None

        self._last_dismissed = now
        self._last_ring = None
        self.hass.bus.async_fire(
            EVENT_DISMISSED,
            {
                **self._base_event_data(),
                "ring_at": ring_at.isoformat() if ring_at else None,
                "dismissed_at": now.isoformat(),
                "delay_seconds": delay,
            },
        )
        self._save()
        self._notify()

    @callback
    def _changed(self) -> None:
        self._schedule(catch_up=True)
        self._save()
        self._notify()

    # ------------------------------------------------------------------
    # Planification
    # ------------------------------------------------------------------
    @callback
    def _cancel_timer(self) -> None:
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None

    @callback
    def _schedule(self, catch_up: bool = False) -> None:
        """Planifie le prochain événement.

        catch_up=True : si on est déjà dans la fenêtre de progression suite à une
        modification (ex. changement d'heure), émet `reveil_pre_ring` tout de suite.
        """
        self._cancel_timer()
        now = dt_util.now()
        ring_at = compute_next_ring(
            now,
            [self._days[d] for d in DAYS],
            [self.effective_time(d) for d in DAYS],
            enabled=self._enabled,
        )
        self._next_ring = ring_at
        if ring_at is None:
            return

        lead = self.lead_minutes
        if lead > 0:
            pre_at = dt_util.as_utc(ring_at) - timedelta(minutes=lead)
            if now < pre_at:
                self._arm_pre_ring(ring_at, pre_at)
                return
            if catch_up and self._pre_fired_key != ring_at.isoformat():
                self._fire_pre_ring(ring_at)
        self._arm_ring(ring_at)

    @callback
    def _arm_pre_ring(self, ring_at: datetime, pre_at: datetime) -> None:
        @callback
        def _on_pre_ring(_now: datetime) -> None:
            self._fire_pre_ring(ring_at)
            self._arm_ring(ring_at)
            self._notify()

        self._unsub_timer = async_track_point_in_time(self.hass, _on_pre_ring, pre_at)

    @callback
    def _arm_ring(self, ring_at: datetime) -> None:
        @callback
        def _on_ring(_now: datetime) -> None:
            self._last_ring = ring_at
            self.hass.bus.async_fire(EVENT_RING, self._ring_event_data(ring_at))
            self._save()
            self._schedule()
            self._notify()

        self._unsub_timer = async_track_point_in_time(self.hass, _on_ring, ring_at)

    @callback
    def _fire_pre_ring(self, ring_at: datetime) -> None:
        self._pre_fired_key = ring_at.isoformat()
        remaining = max(
            0, int((dt_util.as_utc(ring_at) - dt_util.utcnow()).total_seconds())
        )
        self.hass.bus.async_fire(
            EVENT_PRE_RING,
            self._ring_event_data(ring_at, remaining_seconds=remaining),
        )

    @callback
    def _on_midnight(self, _now: datetime) -> None:
        self._notify()

    # ------------------------------------------------------------------
    # Données d'événements et persistance
    # ------------------------------------------------------------------
    def _base_event_data(self) -> dict[str, Any]:
        device = dr.async_get(self.hass).async_get_device(
            identifiers={(DOMAIN, self.entry.entry_id)}
        )
        return {
            "alarm_id": self.entry.entry_id,
            "device_id": device.id if device else None,
            "name": self.entry.title,
        }

    def _ring_event_data(self, ring_at: datetime, **extra: Any) -> dict[str, Any]:
        local = dt_util.as_local(ring_at)
        return {
            **self._base_event_data(),
            "ring_at": local.isoformat(),
            "alarm_time": local.strftime("%H:%M:%S"),
            "weekday": DAYS[local.weekday()],
            "lead_minutes": self.lead_minutes,
            **extra,
        }

    def _as_dict(self) -> dict[str, Any]:
        return {
            "default_time": self._default_time.isoformat(),
            "day_times": {
                d: (t.isoformat() if t else None) for d, t in self._day_times.items()
            },
            "days": dict(self._days),
            "enabled": self._enabled,
            "last_dismissed": (
                self._last_dismissed.isoformat() if self._last_dismissed else None
            ),
            "last_ring": self._last_ring.isoformat() if self._last_ring else None,
        }

    @callback
    def _save(self) -> None:
        self._store.async_delay_save(self._as_dict, 1)
