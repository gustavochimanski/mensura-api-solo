"""
Inicializador do domínio Pedidos.
Responsável por criar tabelas e dados iniciais do domínio.
"""
import logging

from app.database.domain.base import DomainInitializer
from app.database.domain.registry import register_domain

# Importar models do domínio
from app.api.pedidos.models.model_pedido import PedidoModel
from app.api.pedidos.models.model_pedido_item import PedidoUnificadoItemModel
from app.api.pedidos.models.model_pedido_historico import PedidoHistoricoModel

logger = logging.getLogger(__name__)


class PedidosInitializer(DomainInitializer):
    """Inicializador do domínio Pedidos."""
    
    def get_domain_name(self) -> str:
        return "pedidos"
    
    def get_schema_name(self) -> str:
        return "pedidos"
    
    def initialize_data(self) -> None:
        """Popula dados iniciais do domínio Pedidos."""
        # Por enquanto, não há dados iniciais a serem populados
        # No futuro, pode ser necessário popular ENUMs ou dados padrão
        pass


# Cria e registra a instância do inicializador
_pedidos_initializer = PedidosInitializer()
register_domain(_pedidos_initializer)

