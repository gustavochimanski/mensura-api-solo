from __future__ import annotations

from datetime import datetime, time
from typing import Any, Iterable, Optional

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


def _parse_hhmm(value: str) -> Optional[time]:
    """
    Aceita 'HH:MM' (00-23 / 00-59). Retorna None se inválido.
    """
    if not isinstance(value, str):
        return None
    value = value.strip()
    if len(value) != 5 or value[2] != ":":
        return None
    hh, mm = value.split(":")
    if not (hh.isdigit() and mm.isdigit()):
        return None
    h, m = int(hh), int(mm)
    if h < 0 or h > 23 or m < 0 or m > 59:
        return None
    return time(hour=h, minute=m)


def _to_local(now: datetime, tz_name: str | None) -> datetime:
    if not tz_name:
        return now
    if ZoneInfo is None:
        return now
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        return now
    try:
        # Se vier naive, assume já está no TZ do banco/servidor
        if now.tzinfo is None:
            return now.replace(tzinfo=tz)
        return now.astimezone(tz)
    except Exception:
        return now


def _weekday_sun0(local_dt: datetime) -> int:
    """
    Converte datetime.weekday() (0=segunda..6=domingo) para 0=domingo..6=sábado.
    """
    return (local_dt.weekday() + 1) % 7


def _interval_contains(start: time, end: time, t: time) -> bool:
    """
    Retorna True se t estiver dentro do intervalo.
    - Intervalo normal: start < end  => start <= t < end
    - Overnight: start > end         => t >= start OR t < end
    """
    if start == end:
        return False
    if start < end:
        return start <= t < end
    # overnight
    return (t >= start) or (t < end)


def empresa_esta_aberta_agora(
    *,
    horarios_funcionamento: Any,
    timezone: str | None = "America/Sao_Paulo",
    now: datetime | None = None,
) -> Optional[bool]:
    """
    Avalia se a empresa está aberta no horário informado.

    Returns:
        - True/False: quando existe um horário configurado e foi possível avaliar.
        - None: quando não há horário configurado (não força "fechado").

    Formato esperado:
      horarios_funcionamento = [
        {"dia_semana": 0..6, "intervalos": [{"inicio":"HH:MM","fim":"HH:MM"}]}
      ]
      dia_semana: 0=domingo, 1=segunda, ..., 6=sábado
    """
    if not horarios_funcionamento:
        return None
    if not isinstance(horarios_funcionamento, list):
        return None

    now = now or datetime.now()
    local_dt = _to_local(now, timezone)
    dow = _weekday_sun0(local_dt)
    t = local_dt.time()

    def iter_day_entries(entries: Iterable[dict], day: int) -> Iterable[dict]:
        for e in entries:
            if not isinstance(e, dict):
                continue
            if e.get("dia_semana") == day:
                yield e

    def iter_intervals(day_entries: Iterable[dict]) -> Iterable[tuple[time, time]]:
        for e in day_entries:
            intervals = e.get("intervalos") or []
            if not isinstance(intervals, list):
                continue
            for it in intervals:
                if not isinstance(it, dict):
                    continue
                start = _parse_hhmm(it.get("inicio"))
                end = _parse_hhmm(it.get("fim"))
                if start and end:
                    yield (start, end)

    entries = horarios_funcionamento

    # 1) Intervalos do dia atual
    for start, end in iter_intervals(iter_day_entries(entries, dow)):
        if _interval_contains(start, end, t):
            return True

    # 2) Intervalos overnight do dia anterior que avançam para hoje
    prev_dow = (dow - 1) % 7
    for start, end in iter_intervals(iter_day_entries(entries, prev_dow)):
        if start > end and t < end:
            return True

    return False


