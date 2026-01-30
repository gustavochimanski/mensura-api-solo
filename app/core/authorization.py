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


def _assert_user_has_empresa_access(db: Session, user: UserModel, empresa_id: int) -> None:
    """
    Garante que o usuário possa atuar na empresa (tenant) informada.

    Regras:
    - Usuário `type_user='super'` pode acessar qualquer empresa.
    - Caso contrário, exige vínculo explícito em `cadastros.usuario_empresa`,
      OU existência de pelo menos uma permissão em `cadastros.user_permissions`
      (alguns fluxos legados gravavam permissões antes do vínculo).
    """
    # Super (tenant-global)
    if getattr(user, "type_user", None) == "super":
        return

    user_id = int(getattr(user, "id", 0) or 0)
    # Se o usuário não está vinculado à empresa, é tentativa de troca de tenant.
    stmt = select(usuario_empresa.c.empresa_id).where(
        usuario_empresa.c.usuario_id == user_id,
        usuario_empresa.c.empresa_id == empresa_id,
    )
    ok = db.execute(stmt).first()
    if ok:
        return

    # Fallback: se existirem permissões do usuário nessa empresa, considera acesso válido
    # (evita 403 em setups onde o vínculo não foi persistido, mas as permissões sim).
    has_perm = db.execute(
        select(UserPermissionModel.permission_id).where(
            UserPermissionModel.user_id == user_id,
            UserPermissionModel.empresa_id == empresa_id,
        ).limit(1)
    ).first()
    if has_perm:
        return

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
    def _has_key(key: str) -> bool:
        """
        Checa presença considerando normalização básica de rotas:
        - permite equivalência com/sem barra final em chaves `route:/...`
        """
        if key in user_keys:
            return True
        if key.startswith("route:/"):
            if key.endswith("/"):
                return key.rstrip("/") in user_keys
            return f"{key}/" in user_keys
        return False

    # Aliases de permissões (tratadas como equivalentes).
    # No frontend "Dashboard" e "Relatórios" são uma única área.
    if required_key in ("route:/dashboard", "route:/relatorios"):
        # Compatibilidade: alguns setups usam chaves por domínio "relatorios:*"
        # (não no formato "route:/..."). Se existir, considera equivalente.
        if "relatorios:*" in user_keys or "relatorios:read" in user_keys:
            return True

        if _has_key("route:/dashboard") or _has_key("route:/relatorios"):
            return True

    # Equivalência inversa: se o backend exigir permissão por domínio `relatorios:*`,
    # aceitar também as permissões por rota (Dashboard/Relatórios).
    if required_key == "relatorios:*":
        if "relatorios:*" in user_keys:
            return True
        if _has_key("route:/dashboard") or _has_key("route:/relatorios"):
            return True

    if _has_key(required_key):
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
    Exige empresa_id e carrega permissões do usuário nessa empresa (tenant).
    """
    empresa_id = _extract_empresa_id(request)

    if empresa_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empresa_id é obrigatório (use X-Empresa-Id ou query empresa_id)",
        )

    _assert_user_has_empresa_access(db, user=current_user, empresa_id=empresa_id)
    keys = _load_user_permission_keys(db, user_id=current_user.id, empresa_id=empresa_id)
    return AuthzContext(user=current_user, empresa_id=empresa_id, permission_keys=keys)


def require_permissions(required: Iterable[str]):
    required_list = list(required)

    def dependency(ctx: AuthzContext = Depends(get_authz_context)) -> AuthzContext:
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


def require_any_permissions(required: Iterable[str]):
    """
    Variante "OR": permite acesso se o usuário possuir pelo menos uma das permissões.
    """
    required_list = list(required)

    def dependency(ctx: AuthzContext = Depends(get_authz_context)) -> AuthzContext:
        if any(_is_satisfied(k, ctx.permission_keys) for k in required_list):
            return ctx

        logger.warning(
            "[AUTHZ] Acesso negado user_id=%s empresa_id=%s required_any=%s",
            getattr(ctx.user, "id", None),
            ctx.empresa_id,
            required_list,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este recurso",
        )

    return dependency


def require_domain(domain: str, action: str = "read"):
    """
    Atalho por domínio.

    **IMPORTANTE**: o sistema não diferencia mais `:read`/`:write`.
    O backend trabalha apenas com wildcard por domínio (`<dominio>:*`).
    O parâmetro `action` é mantido só por compatibilidade.
    """
    return require_permissions([f"{domain}:*"])

