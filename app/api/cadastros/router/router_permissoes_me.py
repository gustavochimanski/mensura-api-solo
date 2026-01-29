from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.authorization import AuthzContext, get_authz_context
from app.database.db_connection import get_db
from app.api.cadastros.models.model_permission import PermissionModel
from app.api.cadastros.schemas.schema_permissions import UserPermissionKeysResponse


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

router = APIRouter(
    prefix="/api/mensura/permissoes",
    tags=["Mensura - Permissões"],
    # Só para o Swagger documentar o header/query de empresa.
    dependencies=[Depends(_empresa_id_openapi)],
)


@router.get("/me", response_model=UserPermissionKeysResponse, include_in_schema=False)
def listar_minhas_permissoes(
    ctx: AuthzContext = Depends(get_authz_context),
    db: Session = Depends(get_db),
):
    # Admin operacional: devolve catálogo completo para UX do frontend (menu/guards).
    if "*:*" in ctx.permission_keys:
        all_keys = [k for (k,) in db.query(PermissionModel.key).order_by(PermissionModel.key.asc()).all()]
        return UserPermissionKeysResponse(
            user_id=ctx.user.id,
            empresa_id=int(ctx.empresa_id or 0),
            permission_keys=all_keys,
        )

    return UserPermissionKeysResponse(
        user_id=ctx.user.id,
        empresa_id=int(ctx.empresa_id or 0),
        permission_keys=sorted(ctx.permission_keys),
    )

