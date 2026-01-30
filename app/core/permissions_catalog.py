from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class PermissionDef:
    key: str
    domain: str
    description: str | None = None


def get_default_permissions() -> List[PermissionDef]:
    """
    Catálogo canônico de permissões.

    Formato suportado:
    - **route:/...**: permissões por tela/rota do Supervisor (frontend)
    """

    # Rotas (Supervisor)
    routes = [
        ("route:/dashboard", "Dashboard"),
        ("route:/pedidos", "Pedidos"),
        ("route:/cardapio", "Cardápio"),
        ("route:/mesas", "Mesas"),
        ("route:/cadastros", "Cadastros"),
        ("route:/cadastros:clientes", "Cadastros - Clientes"),
        ("route:/cadastros:produtos", "Cadastros - Produtos"),
        ("route:/cadastros:complementos", "Cadastros - Complementos"),
        ("route:/cadastros:receitas", "Cadastros - Receitas"),
        ("route:/cadastros:combos", "Cadastros - Combos"),
        ("route:/cadastros:meios-pagamento", "Cadastros - Meios de pagamento"),
        ("route:/cadastros:regioes-entrega", "Cadastros - Regiões de entrega"),
        ("route:/marketing", "Marketing"),
        ("route:/relatorios", "Relatórios"),
        ("route:/chatbot", "Chatbot"),
        ("route:/atendimentos", "Atendimentos"),
        ("route:/financeiro", "Financeiro"),
        ("route:/financeiro:caixas", "Financeiro - Caixas"),
        ("route:/financeiro:acertos-entregadores", "Financeiro - Acertos entregadores"),
        ("route:/configuracoes", "Configurações"),
        ("route:/configuracoes:empresas", "Configurações - Empresas"),
        ("route:/configuracoes:regioes-entrega", "Configurações - Regiões de entrega"),
        ("route:/configuracoes:meios-pagamento", "Configurações - Meios de pagamento"),
        ("route:/configuracoes:entregadores", "Configurações - Entregadores"),
        ("route:/configuracoes:usuarios", "Configurações - Usuários"),
        ("route:/configuracoes:permissoes", "Configurações - Permissões"),
        ("route:/bi", "BI"),
        ("route:/bi:entregador-detalhado", "BI - Entregador detalhado"),
        ("route:/bi:cliente-detalhado", "BI - Cliente detalhado"),
        ("route:/empresas", "Empresas"),
    ]

    return [PermissionDef(key=k, domain="routes", description=desc) for (k, desc) in routes]

