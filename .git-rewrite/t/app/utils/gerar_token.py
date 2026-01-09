import secrets
import hashlib
import base64

def gerar_super_token():
    # 32 bytes aleatórios
    raw = secrets.token_bytes(32)  # 32 bytes aleatórios = 256 bits
    # opcional: hash SHA256 para uniformidade
    hashed = hashlib.sha256(raw).digest()
    # codifica em base64 url-safe
    token = base64.urlsafe_b64encode(hashed).rstrip(b'=').decode('ascii')
    return token
