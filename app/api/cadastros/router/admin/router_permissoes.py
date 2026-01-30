from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.admin_dependencies import require_admin
from app.core.authorization import AuthzContext, get_authz_context
from app.database.db_connection import get_db
from app.api.cadastros.models.association_tables import usuario_empresa
from app.api.cadastros.models.model_permission import PermissionModel
from app.api.cadastros.models.model_user_permission import UserPermissionModel
from app.api.cadastros.models.user_model import UserModel
from app.api.empresas.models.empresa_model import EmpresaModel
from app.api.cadastros.schemas.schema_permissions import (
    PermissionResponse,
    SetUserPermissionsRequest,
    UserPermissionKeysResponse,
)

router = APIRouter(
    prefix="/api/mensura/admin/permissoes",
    tags=["Admin - Mensura - Permissões"],
    dependencies=[Depends(require_admin)],
    # Mesmo com `redirect_slashes=False` no app, este router aceita / e sem /
    # sem precisar duplicar decorators.
    redirect_slashes=True,
)

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
    # Não valida aqui; a validação/obrigatoriedade é feita em `get_authz_context`.
    return x_empresa_id or empresa_id

router_me = APIRouter(
    prefix="/api/mensura/permissoes",
    tags=["Mensura - Permissões"],
    # Só para o Swagger documentar o header/query de empresa.
    dependencies=[Depends(_empresa_id_openapi)],
    redirect_slashes=True,
)


@router_me.get("/me", response_model=UserPermissionKeysResponse)
def listar_minhas_permissoes(
    ctx: AuthzContext = Depends(get_authz_context),
    db: Session = Depends(get_db),
):
    return UserPermissionKeysResponse(
        user_id=ctx.user.id,
        empresa_id=int(ctx.empresa_id or 0),
        permission_keys=sorted(ctx.permission_keys),
    )


@router.get("", response_model=List[PermissionResponse])
def listar_catalogo_permissoes(db: Session = Depends(get_db)):
    return db.query(PermissionModel).order_by(PermissionModel.domain.asc(), PermissionModel.key.asc()).all()


@router.get("/usuarios/{user_id}/empresas/{empresa_id}", response_model=UserPermissionKeysResponse)
def listar_permissoes_usuario_empresa(
    user_id: int,
    empresa_id: int,
    db: Session = Depends(get_db),
):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    empresa = db.query(EmpresaModel).filter(EmpresaModel.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    rows = (
        db.execute(
            select(PermissionModel.key)
            .select_from(UserPermissionModel)
            .join(PermissionModel, PermissionModel.id == UserPermissionModel.permission_id)
            .where(
                UserPermissionModel.user_id == user_id,
                UserPermissionModel.empresa_id == empresa_id,
            )
        )
        .all()
    )
    keys = sorted({r[0] for r in rows})
    return UserPermissionKeysResponse(user_id=user_id, empresa_id=empresa_id, permission_keys=keys)


@router.put("/usuarios/{user_id}/empresas/{empresa_id}", response_model=UserPermissionKeysResponse)
def definir_permissoes_usuario_empresa(
    user_id: int,
    empresa_id: int,
    payload: SetUserPermissionsRequest,
    db: Session = Depends(get_db),
):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    empresa = db.query(EmpresaModel).filter(EmpresaModel.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Garante vínculo usuario_empresa (idempotente via NOT EXISTS).
    # Isso evita o fluxo "travado" (não havia endpoint dedicado para vincular usuário↔empresa).
    db.execute(
        text(
            """
            INSERT INTO cadastros.usuario_empresa (usuario_id, empresa_id)
            SELECT :user_id, :empresa_id
            WHERE NOT EXISTS (
              SELECT 1
              FROM cadastros.usuario_empresa ue
              WHERE ue.usuario_id = :user_id AND ue.empresa_id = :empresa_id
            )
            """
        ),
        {"user_id": int(user_id), "empresa_id": int(empresa_id)},
    )

    requested_keys = sorted(set(payload.permission_keys or []))

    if requested_keys:
        known = db.execute(select(PermissionModel.key).where(PermissionModel.key.in_(requested_keys))).all()
        known_keys = {r[0] for r in known}
        unknown = [k for k in requested_keys if k not in known_keys]
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permissões inválidas/desconhecidas: {unknown}",
            )

        perm_ids = db.execute(
            select(PermissionModel.id, PermissionModel.key).where(PermissionModel.key.in_(requested_keys))
        ).all()
        key_to_id = {k: pid for (pid, k) in perm_ids}
        new_rows = [
            UserPermissionModel(user_id=user_id, empresa_id=empresa_id, permission_id=key_to_id[k])
            for k in requested_keys
        ]
    else:
        new_rows = []

    # Replace total (set)
    db.query(UserPermissionModel).filter(
        UserPermissionModel.user_id == user_id,
        UserPermissionModel.empresa_id == empresa_id,
    ).delete(synchronize_session=False)

    if new_rows:
        db.add_all(new_rows)

    db.flush()

    return UserPermissionKeysResponse(user_id=user_id, empresa_id=empresa_id, permission_keys=requested_keys)

