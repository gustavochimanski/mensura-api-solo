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

forbidden_exception = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Você não tem permissão para acessar este recurso",
)


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> UserModel:
    """
    Recupera o usuário autenticado a partir do header Authorization (Bearer <token>).
    """
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


def require_type_user(allowed_types: list[str]):
    """
    Dependency factory para restringir acesso por tipo de usuário.
    Exemplo de uso em rota:

        @router.get(..., dependencies=[Depends(require_type_user(['admin']))])
        def rota_somente_admin(...):
            ...
    """

    def dependency(current_user: UserModel = Depends(get_current_user)) -> UserModel:
        if current_user.type_user not in allowed_types:
            logger.warning(
                "[AUTH] Acesso negado. type_user=%s, permitido=%s",
                current_user.type_user,
                allowed_types,
            )
            raise forbidden_exception
        return current_user

    return dependency


def require_admin(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """
    Atalho para rotas que só podem ser acessadas por usuários type_user='admin'.
    """
    if current_user.type_user != "admin":
        logger.warning(
            "[AUTH] Acesso negado. type_user=%s tentou acessar rota admin.",
            current_user.type_user,
        )
        raise forbidden_exception
    return current_user

