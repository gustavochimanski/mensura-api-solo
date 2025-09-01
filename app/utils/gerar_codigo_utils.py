import random
from datetime import datetime, timedelta

# 🔑 Armazenamento temporário de códigos (pode depois ir para Redis)
codigos_temp = {}

def gerar_codigo_telefone(telefone: str) -> str:
    codigo = f"{random.randint(100000, 999999)}"
    # salva com expiração de 5 min
    codigos_temp[telefone] = {"codigo": codigo, "expira_em": datetime.utcnow() + timedelta(minutes=5)}
    # aqui você integraria com SMS real
    print(f"[SMS] Código para {telefone}: {codigo}")
    return codigo

def validar_codigo_telefone(telefone: str, codigo: str) -> bool:
    info = codigos_temp.get(telefone)
    if not info:
        return False
    if datetime.utcnow() > info["expira_em"]:
        return False
    return info["codigo"] == codigo

import random

def gerar_codigo_otp() -> str:
    return f"{random.randint(100000, 999999)}"
