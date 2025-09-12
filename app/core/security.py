# app/core/security.py
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt
from app.config.settings import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# Validação de SECRET_KEY
if not SECRET_KEY or not isinstance(SECRET_KEY, str):
    raise RuntimeError("SECRET_KEY não configurada. Defina SECRET_KEY no .env ou variáveis de ambiente.")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """ Compara senha em texto plano com o hash armazenado no banco."""
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    """ Gera hash bcrypt para armazenar no cadastro de usuário. """
    return pwd_context.hash(password)

# app/core/security.py
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        # garante que sempre é string:
        "sub": str(to_encode.get("sub", ""))
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
