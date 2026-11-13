"""Tests de `custom_components/reveil/schedule.py` (logique pure)."""

from __future__ import annotations

from datetime import datetime, time
from types import ModuleType
from zoneinfo import ZoneInfo

import pytest

ZURICH = ZoneInfo("Europe/Zurich")

ALL_DAYS = [True] * 7
NO_DAYS = [False] * 7
EVERY_DAY_AT_7 = [time(7, 0)] * 7


def at(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    """Un instant « aware » dans le fuseau local de l'utilisateur."""
    return datetime(year, month, day, hour, minute, tzinfo=ZURICH)


# ---------------------------------------------------------------------------
# Cas nominal : aujourd'hui, puis les jours suivants
# ---------------------------------------------------------------------------
def test_ring_later_today(schedule: ModuleType) -> None:
    """Heure encore à venir aujourd'hui → aujourd'hui."""
    monday = at(2026, 11, 16, 5, 0)
    assert schedule.next_ring(monday, ALL_DAYS, EVERY_DAY_AT_7) == at(2026, 11, 16, 7, 0)


def test_ring_tomorrow_when_today_passed(schedule: ModuleType) -> None:
    """Heure du jour déjà passée → lendemain."""
    monday = at(2026, 11, 16, 9, 30)
    assert schedule.next_ring(monday, ALL_DAYS, EVERY_DAY_AT_7) == at(2026, 11, 17, 7, 0)


def test_ring_is_strictly_after_now(schedule: ModuleType) -> None:
    """Pile à l'heure de la sonnerie, on renvoie l'occurrence suivante."""
    monday_7 = at(2026, 11, 16, 7, 0)
    assert schedule.next_ring(monday_7, ALL_DAYS, EVERY_DAY_AT_7) == at(2026, 11, 17, 7, 0)


def test_ring_weekday_index_matches_python_weekday(schedule: ModuleType) -> None:
    """Index 0 = lundi, comme `datetime.weekday()`."""
    # Lundi 16.11.2026 05:00, seul lundi est actif.
    monday = at(2026, 11, 16, 5, 0)
    active = [True] + [False] * 6
    assert schedule.next_ring(monday, active, EVERY_DAY_AT_7) == at(2026, 11, 16, 7, 0)

    # Dimanche 15.11.2026 05:00 : lundi est le lendemain, index 0.
    sunday = at(2026, 11, 15, 5, 0)
    assert schedule.next_ring(sunday, active, EVERY_DAY_AT_7) == at(2026, 11, 16, 7, 0)


def test_only_active_day_wraps_to_next_week(schedule: ModuleType) -> None:
    """Seul aujourd'hui est actif et l'heure est passée → dans 7 jours."""
    monday = at(2026, 11, 16, 8, 0)
    active = [True] + [False] * 6
    assert schedule.next_ring(monday, active, EVERY_DAY_AT_7) == at(2026, 11, 23, 7, 0)


def test_weekend_only(schedule: ModuleType) -> None:
    """Samedi/dimanche seuls : depuis un mercredi, on saute au samedi."""
    active = [False] * 5 + [True, True]
    wednesday = at(2026, 11, 18, 12, 0)
    assert schedule.next_ring(wednesday, active, EVERY_DAY_AT_7) == at(2026, 11, 21, 7, 0)


# ---------------------------------------------------------------------------
# Heures par jour
# ---------------------------------------------------------------------------
def test_per_day_times(schedule: ModuleType) -> None:
    """Chaque jour utilise sa propre heure, y compris après un jour inactif."""
    times = [
        time(6, 15),  # lundi
        time(6, 30),  # mardi
        time(7, 0),   # mercredi
        time(7, 45),  # jeudi
        time(8, 0),   # vendredi
        time(9, 0),   # samedi
        time(10, 30), # dimanche
    ]
    # Lundi 09:00 : lundi (06:15) est passé → mardi 17.11 06:30.
    assert schedule.next_ring(at(2026, 11, 16, 9, 0), ALL_DAYS, times) == at(2026, 11, 17, 6, 30)
    # Samedi 08:30 : samedi (09:00) encore à venir.
    assert schedule.next_ring(at(2026, 11, 21, 8, 30), ALL_DAYS, times) == at(2026, 11, 21, 9, 0)
    # Samedi 09:30 : samedi passé → dimanche 10:30.
    assert schedule.next_ring(at(2026, 11, 21, 9, 30), ALL_DAYS, times) == at(2026, 11, 22, 10, 30)


def test_time_seconds_are_preserved(schedule: ModuleType) -> None:
    """Les secondes de l'heure configurée ne sont pas tronquées."""
    times = [time(6, 30, 15)] * 7
    result = schedule.next_ring(at(2026, 11, 16, 5, 0), ALL_DAYS, times)
    assert result == datetime(2026, 11, 16, 6, 30, 15, tzinfo=ZURICH)


# ---------------------------------------------------------------------------
# Absence de prochaine sonnerie
# ---------------------------------------------------------------------------
def test_disabled_returns_none(schedule: ModuleType) -> None:
    assert schedule.next_ring(at(2026, 11, 16, 5, 0), ALL_DAYS, EVERY_DAY_AT_7, enabled=False) is None


def test_no_active_day_returns_none(schedule: ModuleType) -> None:
    assert schedule.next_ring(at(2026, 11, 16, 5, 0), NO_DAYS, EVERY_DAY_AT_7) is None


@pytest.mark.parametrize(
    "active,times",
    [
        ([True] * 6, EVERY_DAY_AT_7),
        ([True] * 8, EVERY_DAY_AT_7),
        (ALL_DAYS, [time(7, 0)] * 6),
        (ALL_DAYS, []),
        ([], []),
    ],
)
def test_wrong_lengths_return_none(
    schedule: ModuleType, active: list[bool], times: list[time]
) -> None:
    """Une configuration incomplète ne doit pas inventer de sonnerie."""
    assert schedule.next_ring(at(2026, 11, 16, 5, 0), active, times) is None


# ---------------------------------------------------------------------------
# Changements d'heure (Europe/Zurich)
# ---------------------------------------------------------------------------
def test_dst_spring_forward(schedule: ModuleType) -> None:
    """Nuit du 28 au 29 mars 2026 : 02:00 → 03:00, la sonnerie de 07:00 reste à 07:00 locale."""
    now = at(2026, 3, 28, 23, 30)  # CET, UTC+1
    result = schedule.next_ring(now, ALL_DAYS, EVERY_DAY_AT_7)
    assert result == at(2026, 3, 29, 7, 0)  # CEST, UTC+2
    assert result.utcoffset().total_seconds() == 2 * 3600


def test_dst_fall_back(schedule: ModuleType) -> None:
    """Nuit du 24 au 25 octobre 2026 : 03:00 → 02:00, la sonnerie de 07:00 reste à 07:00 locale."""
    now = at(2026, 10, 24, 23, 30)  # CEST, UTC+2
    result = schedule.next_ring(now, ALL_DAYS, EVERY_DAY_AT_7)
    assert result == at(2026, 10, 25, 7, 0)  # déjà CET : bascule à 03:00
    assert result.utcoffset().total_seconds() == 3600


def test_day_after_dst_fall_back(schedule: ModuleType) -> None:
    """Le lundi suivant la bascule est bien en heure d'hiver."""
    now = at(2026, 10, 25, 12, 0)  # CET, UTC+1
    result = schedule.next_ring(now, ALL_DAYS, EVERY_DAY_AT_7)
    assert result == at(2026, 10, 26, 7, 0)
    assert result.utcoffset().total_seconds() == 3600


# ---------------------------------------------------------------------------
# Invariants sur une semaine entière
# ---------------------------------------------------------------------------
def test_result_always_on_an_active_day_at_the_configured_time(schedule: ModuleType) -> None:
    """Propriété : le résultat tombe sur un jour actif, à son heure, dans le futur."""
    times = [time(6, 0), time(6, 15), time(6, 30), time(6, 45), time(7, 0), time(7, 15), time(7, 30)]
    active = [True, False, True, False, True, False, True]

    for day in range(16, 23):  # 16 → 22 novembre 2026
        for hour in range(24):
            now = at(2026, 11, day, hour, 30)
            result = schedule.next_ring(now, active, times)
            assert result is not None
            assert result > now
            assert active[result.weekday()]
            assert result.time() == times[result.weekday()]
            assert (result - now).days < 8
