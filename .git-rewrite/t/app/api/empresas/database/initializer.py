"""
Inicializador do domínio Empresas.
Responsável por criar tabelas e dados iniciais do domínio.
"""
import logging

from app.database.domain.base import DomainInitializer
from app.database.domain.registry import register_domain

# Importar models do domínio
from app.api.empresas.models.empresa_model import EmpresaModel

logger = logging.getLogger(__name__)


class EmpresasInitializer(DomainInitializer):
    """Inicializador do domínio Empresas."""
    
    def get_domain_name(self) -> str:
        return "empresas"
    
    def get_schema_name(self) -> str:
        return "cadastros"  # Mantém o schema cadastros por compatibilidade


# Cria e registra a instância do inicializador
_empresas_initializer = EmpresasInitializer()
register_domain(_empresas_initializer)

