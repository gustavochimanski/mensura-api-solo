from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Set

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger
from app.api.cadastros.models.user_model import UserModel
from app.api.cadastros.models.association_tables import usuario_empresa
from app.api.cadastros.models.model_permission import PermissionModel
from app.api.cadastros.models.model_user_permission import UserPermissionModel


@dataclass(frozen=True)
class AuthzContext:
    user: UserModel
    empresa_id: Optional[int]
    permission_keys: Set[str]


def _extract_empresa_id(request: Request) -> Optional[int]:
    """
    Extrai empresa_id do request.

    Compatibilidade:
    - Header: X-Empresa-Id
    - Query:  empresa_id / id_empresa
    """
    header_val = request.headers.get("X-Empresa-Id") or request.headers.get("x-empresa-id")
    query_val = request.query_params.get("empresa_id") or request.query_params.get("id_empresa")
    raw = header_val or query_val
    if raw is None or raw == "":
        return None
    try:
        empresa_id = int(raw)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empresa_id inválido (use X-Empresa-Id ou query empresa_id)",
        )
    if empresa_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empresa_id inválido (deve ser > 0)",
        )
    return empresa_id


def _assert_user_has_empresa_access(db: Session, user_id: int, empresa_id: int) -> None:
    # Se o usuário não está vinculado à empresa, é tentativa de troca de tenant.
    stmt = select(usuario_empresa.c.empresa_id).where(
        usuario_empresa.c.usuario_id == user_id,
        usuario_empresa.c.empresa_id == empresa_id,
    )
    ok = db.execute(stmt).first()
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a esta empresa",
        )


def _load_user_permission_keys(db: Session, user_id: int, empresa_id: int) -> Set[str]:
    stmt = (
        select(PermissionModel.key)
        .select_from(UserPermissionModel)
        .join(PermissionModel, PermissionModel.id == UserPermissionModel.permission_id)
        .where(
            UserPermissionModel.user_id == user_id,
            UserPermissionModel.empresa_id == empresa_id,
        )
    )
    rows = db.execute(stmt).all()
    return {r[0] for r in rows}


def _is_satisfied(required_key: str, user_keys: Set[str]) -> bool:
    if required_key in user_keys:
        return True
    # wildcard por domínio: "<domain>:*"
    if ":" in required_key:
        domain = required_key.split(":", 1)[0]
        if f"{domain}:*" in user_keys:
            return True
    return False


def get_authz_context(
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> AuthzContext:
    """
    Carrega contexto para autorização.
    - type_user=admin: bypass (superusuário operacional)
    - caso contrário: exige empresa_id e carrega permissões do usuário nessa empresa.
    """
    empresa_id = _extract_empresa_id(request)

    # Super-admin operacional: mantém compatibilidade e evita "brickar" o sistema.
    if getattr(current_user, "type_user", None) == "admin":
        return AuthzContext(user=current_user, empresa_id=empresa_id, permission_keys=set(["*:*"]))

    if empresa_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empresa_id é obrigatório (use X-Empresa-Id ou query empresa_id)",
        )

    _assert_user_has_empresa_access(db, user_id=current_user.id, empresa_id=empresa_id)
    keys = _load_user_permission_keys(db, user_id=current_user.id, empresa_id=empresa_id)
    return AuthzContext(user=current_user, empresa_id=empresa_id, permission_keys=keys)


def require_permissions(required: Iterable[str]):
    required_list = list(required)

    def dependency(ctx: AuthzContext = Depends(get_authz_context)) -> AuthzContext:
        # bypass admin operacional
        if "*:*" in ctx.permission_keys:
            return ctx

        missing = [k for k in required_list if not _is_satisfied(k, ctx.permission_keys)]
        if missing:
            logger.warning(
                "[AUTHZ] Acesso negado user_id=%s empresa_id=%s required=%s",
                getattr(ctx.user, "id", None),
                ctx.empresa_id,
                missing,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar este recurso",
            )
        return ctx

    return dependency


def require_domain(domain: str, action: str = "read"):
    """
    Atalho por domínio. Exemplos:
    - require_domain("pedidos") -> exige "pedidos:read" (ou "pedidos:*")
    - require_domain("financeiro", "write") -> exige "financeiro:write" (ou "financeiro:*")
    """
    key = f"{domain}:{action}"
    return require_permissions([key])

