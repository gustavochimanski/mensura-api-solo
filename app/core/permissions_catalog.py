from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class PermissionDef:
    key: str
    domain: str
    description: str | None = None


def _rw(domain: str, description_prefix: str) -> list[PermissionDef]:
    return [
        PermissionDef(key=f"{domain}:read", domain=domain, description=f"{description_prefix}: leitura"),
        PermissionDef(key=f"{domain}:write", domain=domain, description=f"{description_prefix}: escrita"),
        PermissionDef(key=f"{domain}:*", domain=domain, description=f"{description_prefix}: acesso total (wildcard)"),
    ]


def get_default_permissions() -> List[PermissionDef]:
    """
    Catálogo canônico de permissões (fonte da verdade).

    - Mantenha as keys estáveis (não renomear sem migração).
    - Use domínios por bounded context/área.
    """
    perms: list[PermissionDef] = []

    perms += _rw("cadastros", "Cadastros")
    perms += _rw("empresas", "Empresas")
    perms += _rw("pedidos", "Pedidos")
    perms += _rw("cardapio", "Cardápio")
    perms += _rw("catalogo", "Catálogo")
    perms += _rw("caixas", "Caixas")
    perms += _rw("financeiro", "Financeiro")
    perms += _rw("notifications", "Notificações")
    perms += _rw("chatbot", "Chatbot")
    perms += _rw("relatorios", "Relatórios")
    perms += _rw("localizacao", "Localização")
    perms += _rw("monitoring", "Monitoring")

    # Domínio "mensura" (rotas administrativas gerais em /api/mensura)
    perms += _rw("mensura", "Mensura (admin)")

    return perms


def iter_permission_keys(perms: Iterable[PermissionDef]) -> list[str]:
    return [p.key for p in perms]

