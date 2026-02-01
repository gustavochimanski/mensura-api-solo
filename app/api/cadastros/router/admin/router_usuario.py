# app/api/mensura/router/router_usuario.py
from typing import List
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.cadastros.services.usuario_service import UserService
from app.api.cadastros.schemas.schema_usuario import UserCreate, UserUpdate, UserResponse
from app.core.admin_dependencies import require_admin
from app.core.authorization import AuthzContext, get_authz_context

def _empresa_id_openapi(
    x_empresa_id: int | None = Header(
        default=None,
        alias="X-Empresa-Id",
        description="ID da empresa (tenant). Recomendado enviar por header.",
    ),
    empresa_id: int | None = Query(
        default=None,
        description="Alternativa ao header X-Empresa-Id.",
    ),
) -> int | None:
    # Não valida aqui; a validação/obrigatoriedade é feita em `get_authz_context`
    # (aplicado via dependencies no include_router).
    return x_empresa_id or empresa_id

router = APIRouter(
    prefix="/api/mensura/admin/usuarios",
    tags=["Admin - Mensura - Usuarios"],
    dependencies=[
        Depends(require_admin),
        # Só para documentar no Swagger o header/query de empresa.
        Depends(_empresa_id_openapi),
    ],
)


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    request: UserCreate,
    ctx: AuthzContext = Depends(get_authz_context),
    db: Session = Depends(get_db),
):
    return UserService(db).create_user(request, empresa_id_scope=ctx.empresa_id, actor=ctx.user)


@router.get("", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    ctx: AuthzContext = Depends(get_authz_context),
    db: Session = Depends(get_db),
):
    return UserService(db).list_users(skip, limit, empresa_id_scope=ctx.empresa_id, actor=ctx.user)


@router.get("/{id}", response_model=UserResponse)
def get_user(
    id: int,
    ctx: AuthzContext = Depends(get_authz_context),
    db: Session = Depends(get_db),
):
    return UserService(db).get_user(id, empresa_id_scope=ctx.empresa_id, actor=ctx.user)


@router.put("/{id}", response_model=UserResponse)
def update_user(
    id: int,
    request: UserUpdate,
    ctx: AuthzContext = Depends(get_authz_context),
    db: Session = Depends(get_db),
):
    return UserService(db).update_user(id, request, empresa_id_scope=ctx.empresa_id, actor=ctx.user)


@router.delete("/{id}", status_code=204)
def delete_user(
    id: int,
    ctx: AuthzContext = Depends(get_authz_context),
    db: Session = Depends(get_db),
):
    UserService(db).delete_user(id, empresa_id_scope=ctx.empresa_id, actor=ctx.user)

