"""
Inicializador do domínio Caixas.

NOTA: Este initializer está mantido apenas para compatibilidade.
O CaixaModel está no schema 'cadastros' e CaixaConferenciaModel está no schema 'financeiro'.
O schema 'caixas' foi removido.
"""
import logging

from app.database.domain.base import DomainInitializer
from app.database.domain.registry import register_domain

# Importar models do domínio (CaixaModel está em cadastros, não precisa de initializer próprio)
from app.api.caixas.models.model_caixa import CaixaModel

logger = logging.getLogger(__name__)


class CaixasInitializer(DomainInitializer):
    """Inicializador do domínio Caixas.
    
    NOTA: CaixaModel está no schema 'cadastros', então este initializer
    não precisa criar tabelas. Está aqui apenas para manter compatibilidade.
    """
    
    def get_domain_name(self) -> str:
        return "caixas"
    
    def get_schema_name(self) -> str:
        return "cadastros"  # CaixaModel está em cadastros
    
    def initialize_tables(self) -> None:
        """Não cria tabelas - CaixaModel está no schema cadastros."""
        # CaixaModel está no schema cadastros, não precisa criar aqui
        pass


# Cria e registra a instância do inicializador (para compatibilidade)
_caixas_initializer = CaixasInitializer()
register_domain(_caixas_initializer)

