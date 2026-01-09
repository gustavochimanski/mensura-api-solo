"""
Inicializador do domínio Financeiro.
Responsável por criar tabelas do domínio Financeiro.
"""
import logging

from app.database.domain.base import DomainInitializer
from app.database.domain.registry import register_domain

# Importar models do domínio
from app.api.financeiro.models.model_caixa_conferencia import CaixaConferenciaModel

logger = logging.getLogger(__name__)


class FinanceiroInitializer(DomainInitializer):
    """Inicializador do domínio Financeiro."""
    
    def get_domain_name(self) -> str:
        return "financeiro"
    
    def get_schema_name(self) -> str:
        return "financeiro"


# Cria e registra a instância do inicializador
_financeiro_initializer = FinanceiroInitializer()
register_domain(_financeiro_initializer)

