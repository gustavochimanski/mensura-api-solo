from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.authorization import AuthzContext, get_authz_context
from app.database.db_connection import get_db
from app.api.cadastros.models.model_permission import PermissionModel
from app.api.cadastros.schemas.schema_permissions import UserPermissionKeysResponse

router = APIRouter(
    prefix="/api/mensura/permissoes",
    tags=["Mensura - Permissões"],
)


@router.get("/me", response_model=UserPermissionKeysResponse)
@router.get("/me/", response_model=UserPermissionKeysResponse, include_in_schema=False)
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

