from datetime import datetime
from zoneinfo import ZoneInfo
#

def now_trimmed():
    """Retorna datetime atual em timezone de São Paulo, sem microsegundos"""
    tz_sp = ZoneInfo('America/Sao_Paulo')
    return datetime.now(tz_sp).replace(microsecond=0)
