from functools import lru_cache
import requests

@lru_cache(maxsize=32)
def feriados_por_ano(ano: int) -> set[str]:
    """Baixa feriados do BrasilAPI e devolve set('YYYY-MM-DD'). Cacheado em memória."""
    url = f"https://brasilapi.com.br/api/feriados/v1/{ano}"
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    return {item["date"] for item in resp.json()}
