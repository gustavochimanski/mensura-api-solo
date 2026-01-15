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
    - Intervalo normal: start < end  => start <= t < end (exclusivo no fim, mas considera até 59 segundos)
    - Overnight: start > end         => t >= start OR t < end
    
    Nota: Quando o horário de fechamento é "23:30", significa que está aberto até 23:30:59,
    então comparamos apenas horas e minutos, ignorando segundos.
    """
    if start == end:
        # Se início e fim são iguais, considera aberto apenas nesse horário exato
        return t.hour == start.hour and t.minute == start.minute
    
    if start < end:
        # Intervalo normal: compara horas e minutos (ignora segundos)
        # Se t está entre start e end (inclusive), está aberto
        t_hm = (t.hour, t.minute)
        start_hm = (start.hour, start.minute)
        end_hm = (end.hour, end.minute)
        
        # Se está no mesmo minuto do início ou depois, e antes ou no mesmo minuto do fim
        if t_hm >= start_hm and t_hm <= end_hm:
            return True
        return False
    
    # overnight (ex: 22:00 até 02:00)
    t_hm = (t.hour, t.minute)
    start_hm = (start.hour, start.minute)
    end_hm = (end.hour, end.minute)
    return (t_hm >= start_hm) or (t_hm <= end_hm)


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
    
    # Logs para debug
    dias_nomes = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
    print(f"      [DEBUG] Hora atual (naive): {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"      [DEBUG] Hora local (timezone {timezone}): {local_dt.strftime('%Y-%m-%d %H:%M:%S') if hasattr(local_dt, 'strftime') else str(local_dt)}")
    print(f"      [DEBUG] Dia da semana: {dow} ({dias_nomes[dow] if dow < len(dias_nomes) else 'Desconhecido'})")
    print(f"      [DEBUG] Hora atual (time): {t.strftime('%H:%M:%S')}")

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
    print(f"      [DEBUG] Verificando intervalos do dia {dow} ({dias_nomes[dow] if dow < len(dias_nomes) else 'Desconhecido'})")
    for start, end in iter_intervals(iter_day_entries(entries, dow)):
        print(f"      [DEBUG] Intervalo: {start.strftime('%H:%M')} - {end.strftime('%H:%M')}, Hora atual: {t.strftime('%H:%M')}")
        contem = _interval_contains(start, end, t)
        print(f"      [DEBUG] Intervalo contém hora atual? {contem}")
        if contem:
            print(f"      [DEBUG] ✅ LOJA ABERTA - encontrado intervalo válido")
            return True

    # 2) Intervalos overnight do dia anterior que avançam para hoje
    prev_dow = (dow - 1) % 7
    print(f"      [DEBUG] Verificando intervalos overnight do dia anterior ({prev_dow})")
    for start, end in iter_intervals(iter_day_entries(entries, prev_dow)):
        if start > end:
            print(f"      [DEBUG] Intervalo overnight: {start.strftime('%H:%M')} - {end.strftime('%H:%M')}, Hora atual: {t.strftime('%H:%M')}")
            contem = _interval_contains(start, end, t)
            print(f"      [DEBUG] Intervalo overnight contém? {contem}")
            if contem:
                print(f"      [DEBUG] ✅ LOJA ABERTA - encontrado intervalo overnight válido")
                return True

    print(f"      [DEBUG] ❌ LOJA FECHADA - nenhum intervalo válido encontrado")
    return False


def formatar_horarios_funcionamento_mensagem(horarios_funcionamento: Any) -> str:
    """
    Formata os horários de funcionamento em uma mensagem bonita para WhatsApp.
    
    Args:
        horarios_funcionamento: Lista de horários no formato esperado
        
    Returns:
        Mensagem formatada com os horários
    """
    if not horarios_funcionamento or not isinstance(horarios_funcionamento, list):
        return "Horários de funcionamento não configurados."
    
    # Nomes dos dias da semana
    dias_semana = {
        0: "Domingo",
        1: "Segunda-feira",
        2: "Terça-feira",
        3: "Quarta-feira",
        4: "Quinta-feira",
        5: "Sexta-feira",
        6: "Sábado"
    }
    
    # Agrupa horários por dia
    horarios_por_dia = {}
    for item in horarios_funcionamento:
        if not isinstance(item, dict):
            continue
        dia = item.get("dia_semana")
        intervalos = item.get("intervalos", [])
        
        if dia is not None and isinstance(intervalos, list) and intervalos:
            if dia not in horarios_por_dia:
                horarios_por_dia[dia] = []
            horarios_por_dia[dia].extend(intervalos)
    
    if not horarios_por_dia:
        return "Horários de funcionamento não configurados."
    
    # Monta a mensagem
    mensagem = "🕐 *HORÁRIOS DE FUNCIONAMENTO*\n\n"
    
    # Ordena os dias (0=domingo até 6=sábado)
    for dia in sorted(horarios_por_dia.keys()):
        nome_dia = dias_semana.get(dia, f"Dia {dia}")
        intervalos = horarios_por_dia[dia]
        
        # Formata os intervalos
        intervalos_formatados = []
        for intervalo in intervalos:
            if isinstance(intervalo, dict):
                inicio = intervalo.get("inicio", "")
                fim = intervalo.get("fim", "")
                if inicio and fim:
                    intervalos_formatados.append(f"{inicio} às {fim}")
        
        if intervalos_formatados:
            horarios_str = " e ".join(intervalos_formatados)
            mensagem += f"• *{nome_dia}:* {horarios_str}\n"
    
    mensagem += "\n💬 Retornaremos em breve quando estivermos abertos!"
    
    return mensagem


