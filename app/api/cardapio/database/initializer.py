"""
Inicializador do domínio Cardápio.
Responsável por criar tabelas do domínio Cardápio.
"""
import logging
from sqlalchemy import text

from app.database.domain.base import DomainInitializer
from app.database.domain.registry import register_domain
from app.database.db_connection import engine, Base

# Importar models do domínio
from app.api.cardapio.models.model_transacao_pagamento_dv import TransacaoPagamentoModel
from app.api.cardapio.models.model_pedido_dv import PedidoDeliveryModel
from app.api.cardapio.models.model_pedido_item_dv import PedidoItemModel
from app.api.cardapio.models.model_pedido_status_historico_dv import PedidoStatusHistoricoModel
from app.api.cardapio.models.model_categoria_dv import CategoriaDeliveryModel
from app.api.cardapio.models.model_vitrine import VitrinesModel

logger = logging.getLogger(__name__)


class CardapioInitializer(DomainInitializer):
    """Inicializador do domínio Cardápio."""
    
    def get_domain_name(self) -> str:
        return "cardapio"
    
    def get_schema_name(self) -> str:
        return "cardapio"
    
    def initialize_tables(self) -> None:
        """Cria as tabelas do domínio Cardápio com ordem específica."""
        # Prioriza criação das tabelas principais primeiro
        cardapio_tables = [
            PedidoDeliveryModel.__table__,
            PedidoItemModel.__table__,
            PedidoStatusHistoricoModel.__table__,
            TransacaoPagamentoModel.__table__
        ]
        
        logger.info(f"📋 Criando tabelas do domínio {self.get_domain_name()}...")
        
        # Cria tabelas principais primeiro
        for table in cardapio_tables:
            try:
                table.create(engine, checkfirst=True)
                logger.info(f"  ✅ Tabela {table.schema}.{table.name} criada/verificada")
            except Exception as e:
                error_msg = str(e)
                if "already exists" in error_msg.lower():
                    logger.info(f"  ℹ️ Tabela {table.schema}.{table.name} já existe")
                else:
                    logger.error(f"  ❌ Erro ao criar tabela {table.schema}.{table.name}: {e}")
                    raise
        
        # Cria as demais tabelas do domínio
        schema_name = self.get_schema_name()
        all_tables = [
            t for t in Base.metadata.sorted_tables
            if t.schema == schema_name and t not in cardapio_tables
        ]
        
        for table in all_tables:
            try:
                table.create(engine, checkfirst=True)
                logger.info(f"  ✅ Tabela {table.schema}.{table.name} criada/verificada")
            except Exception as e:
                error_msg = str(e)
                if "already exists" in error_msg.lower():
                    logger.info(f"  ℹ️ Tabela {table.schema}.{table.name} já existe")
                else:
                    logger.error(f"  ❌ Erro ao criar tabela {table.schema}.{table.name}: {e}")
                    raise
    
    def validate(self) -> bool:
        """Valida se as tabelas principais do cardápio foram criadas."""
        try:
            with engine.connect() as conn:
                tabelas_cardapio = [
                    "pedidos_dv",
                    "pedido_itens_dv",
                    "pedido_status_historico_dv",
                    "transacoes_pagamento_dv"
                ]
                
                for tabela in tabelas_cardapio:
                    result = conn.execute(text("""
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'cardapio' 
                        AND table_name = :tabela
                    """), {"tabela": tabela})
                    if not result.scalar():
                        logger.warning(f"  ⚠️ Tabela {tabela} não encontrada")
                        return False
                
                return True
        except Exception as e:
            logger.warning(f"  ⚠️ Erro ao validar tabelas do cardápio: {e}")
            return False


# Cria e registra a instância do inicializador
_cardapio_initializer = CardapioInitializer()
register_domain(_cardapio_initializer)

