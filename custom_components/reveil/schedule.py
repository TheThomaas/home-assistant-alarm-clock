"""Calcul du prochain réveil (logique pure, sans dépendance à Home Assistant)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, time, timedelta


def next_ring(
    now: datetime,
    active: Sequence[bool],
    times: Sequence[time],
    *,
    enabled: bool = True,
) -> datetime | None:
    """Retourne le prochain déclenchement strictement postérieur à `now`.

    `active` et `times` ont 7 éléments, index 0 = lundi.
    `now` doit être « aware » (fuseau horaire local).
    """
    if not enabled or len(active) != 7 or len(times) != 7 or not any(active):
        return None

    # 8 jours : couvre le cas « seul aujourd'hui est actif et l'heure est passée »
    for offset in range(8):
        day = now.date() + timedelta(days=offset)
        weekday = day.weekday()
        if not active[weekday]:
            continue
        candidate = datetime.combine(day, times[weekday], tzinfo=now.tzinfo)
        if candidate > now:
            return candidate
    return None
