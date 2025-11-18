# app/mensura/router/auth_controller.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.api.auth.auth_repo import AuthRepository
from app.api.auth.schema_auth import LoginRequest, TokenResponse
from app.core.security import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.database.db_connection import get_db


from app.core.admin_dependencies import get_current_user
from app.api.cadastros.schemas.schema_usuario import UserResponse
from app.api.cadastros.models.user_model import UserModel
from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.core.client_dependecies import get_cliente_by_super_token
from pydantic import BaseModel


router = APIRouter(tags=["auth"], prefix="/api/auth")

@router.post("/token", response_model=TokenResponse)
def login_usuario(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    # 1. Busca usuário no banco
    repo = AuthRepository(db)
    user = repo.get_user_by_username(payload.username)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 2. Gera JWT com 30 minutos de validade
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # 3. Retorna o token no corpo (JSON)
    return TokenResponse(
        type_user=user.type_user,
        access_token=access_token,
        token_type="Bearer",
    )

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Retorna o usuário atual baseado no token JWT"
)
def obter_usuario_atual(
    current_user: UserModel = Depends(get_current_user),
):
    """Puxa o usuário já autenticado pelo get_current_user e devolve seus campos."""
    return current_user


class ClienteMeResponse(BaseModel):
    nome: str
    super_token: str
    telefone: str

@router.get(
    "/client/me",
    response_model=ClienteMeResponse,
    summary="Retorna o Cliente atual baseado no x-super-token"
)
def obter_cliente_atual(
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
):
    """Puxa o Cliente já autenticado pelo get_cliente_by_super_token (header X-Super-Token) e retorna apenas nome, token e telefone."""
    return ClienteMeResponse(
        nome=cliente.nome,
        super_token=cliente.super_token,
        telefone=cliente.telefone
    )
