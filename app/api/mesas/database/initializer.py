"""
Inicializador do domínio Mesas.
Responsável por criar tabelas do domínio Mesas.
"""
import logging

from app.database.domain.base import DomainInitializer
from app.database.domain.registry import register_domain

# Importar models do domínio
from app.api.mesas.models.model_mesa import MesaModel
from app.api.mesas.models.model_mesa_historico import MesaHistoricoModel
from app.api.mesas.models.model_pedido_mesa import PedidoMesaModel
from app.api.mesas.models.model_pedido_mesa_item import PedidoMesaItemModel

logger = logging.getLogger(__name__)


class MesasInitializer(DomainInitializer):
    """Inicializador do domínio Mesas."""
    
    def get_domain_name(self) -> str:
        return "mesas"
    
    def get_schema_name(self) -> str:
        return "mesas"


# Cria e registra a instância do inicializador
_mesas_initializer = MesasInitializer()
register_domain(_mesas_initializer)

