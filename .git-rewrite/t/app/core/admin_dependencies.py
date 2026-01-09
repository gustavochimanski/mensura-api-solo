# app/core/admin_dependencies.py

from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.api.cadastros.models.user_model import UserModel
from app.api.auth.auth_repo import AuthRepository
from app.core.security import SECRET_KEY, ALGORITHM
from app.database.db_connection import get_db
from app.utils.logger import logger

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Não autenticado Access",
    headers={"WWW-Authenticate": "Bearer"},
)

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> UserModel:
    # 1. Pega o token do header Authorization
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning("[AUTH] Cabeçalho Authorization ausente ou malformado.")
        raise credentials_exception

    access_token = auth_header.replace("Bearer ", "")

    # 2. Decodifica o JWT
    try:
        payload = jwt.decode(
            access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_sub": False},
        )
        raw_sub = payload.get("sub")
        if raw_sub is None:
            raise credentials_exception
        user_id = int(raw_sub)
    except (JWTError, ValueError) as e:
        logger.error(f"[AUTH] Erro ao decodificar JWT: {e}")
        raise credentials_exception

    # 3. Busca o usuário no banco
    user = AuthRepository(db).get_user_by_id(user_id)
    if not user:
        raise credentials_exception

    return user
