from datetime import date, timedelta
import pandas as pd

def dias_do_mes(ano: int, mes: int) -> list[date]:
    """Retorna todas as datas do mês."""
    inicio = date(ano, mes, 1)
    prox   = inicio.replace(month=mes % 12 + 1, day=1) if mes < 12 else date(ano+1, 1, 1)
    delta  = prox - inicio
    return [inicio + timedelta(days=i) for i in range(delta.days)]

def df_features(datas: list[date], feriados: set[str]) -> pd.DataFrame:
    """Monta DataFrame com features pré-modelo."""
    df = pd.DataFrame({"data": datas})
    df["ano"]        = df.data.dt.year
    df["mes"]        = df.data.dt.month
    df["dia"]        = df.data.dt.day
    df["dia_semana"] = df.data.dt.dayofweek
    df["feriado"]    = df.data.astype(str).isin(feriados).astype(int)
    return df
