"""
Orquestrador central de inicialização do banco de dados.
Coordena a inicialização de infraestrutura e domínios.
"""
import logging
from typing import Optional

from ..infrastructure import (
    habilitar_postgis,
    configurar_timezone,
    criar_schemas,
    criar_enums,
)
from .registry import get_registry
from ..db_connection import engine

logger = logging.getLogger(__name__)


class DatabaseOrchestrator:
    """
    Orquestrador responsável por coordenar a inicialização completa do banco.
    
    Fluxo:
    1. Inicializa infraestrutura compartilhada (PostGIS, timezone, schemas, ENUMs)
    2. Inicializa todos os domínios registrados
    3. Valida inicialização
    """
    
    def __init__(self):
        self.registry = get_registry()
    
    def verificar_banco_inicializado(self) -> bool:
        """
        Verifica se o banco já foi inicializado consultando se as tabelas principais existem.
        
        Returns:
            bool: True se o banco parece estar inicializado
        """
        try:
            from sqlalchemy import text
            
            with engine.connect() as conn:
                # Verifica se existem tabelas principais dos schemas
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema IN ('cardapio', 'cadastros', 'mesas', 'notifications', 'balcao', 'receitas', 'produtos', 'financeiro', 'pedidos')
                    AND table_name IN (
                        'usuarios', 'empresas', 'produtos', 'produtos_empresa', 'categorias',
                        'clientes', 'pedidos_dv', 'enderecos', 'regioes_entrega',
                        'categorias_dv', 'vitrines', 'entregadores_dv', 'meio_pagamento,
                        'cupons_dv', 'transacoes_pagamento_dv', 'pedido_itens_dv',
                        'pedido_status_historico_dv', 'parceiros_dv', 'banner_parceiros_dv'
                    );
                """))
                table_count = result.scalar()
                
                # Se tem pelo menos 15 tabelas principais, considera inicializado
                return table_count >= 15
                
        except Exception as e:
            logger.warning(f"⚠️ Erro ao verificar status de inicialização: {e}")
            return False
    
    def inicializar_infraestrutura(self) -> None:
        """
        Inicializa a infraestrutura compartilhada do banco.
        
        Ordem:
        1. Timezone
        2. PostGIS
        3. Schemas
        4. ENUMs
        
        Raises:
            Exception: Se houver erro em qualquer etapa
        """
        logger.info("📦 Inicializando infraestrutura compartilhada...")
        
        try:
            # 1. Timezone
            logger.info("  → Configurando timezone...")
            configurar_timezone()
            
            # 2. PostGIS
            logger.info("  → Habilitando PostGIS...")
            habilitar_postgis()
            
            # 3. Schemas
            logger.info("  → Criando schemas...")
            criar_schemas()
            
            # 4. ENUMs
            logger.info("  → Criando ENUMs...")
            criar_enums()
            
            logger.info("✅ Infraestrutura inicializada com sucesso.")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar infraestrutura: {e}", exc_info=True)
            raise
    
    def inicializar_dominios(self) -> None:
        """
        Inicializa todos os domínios registrados.
        
        Raises:
            Exception: Se houver erro na inicialização de algum domínio
        """
        initializers = self.registry.get_all()
        
        if not initializers:
            logger.warning("⚠️ Nenhum domínio registrado para inicialização.")
            return
        
        logger.info(f"📦 Inicializando {len(initializers)} domínio(s)...")
        
        for initializer in initializers:
            try:
                initializer.initialize()
            except Exception as e:
                logger.error(
                    f"❌ Erro ao inicializar domínio {initializer.get_domain_name()}: {e}",
                    exc_info=True
                )
                raise
    
    def initialize(self) -> None:
        """
        Função principal que orquestra toda a inicialização do banco.
        
        Fluxo:
        1. Inicializa infraestrutura compartilhada
        2. Inicializa todos os domínios registrados
        
        Raises:
            Exception: Se houver erro em qualquer etapa
        """
        logger.info("🚀 Iniciando processo de inicialização do banco de dados...")
        
        try:
            # Passo 1: Infraestrutura compartilhada
            self.inicializar_infraestrutura()
            
            # Passo 2: Domínios
            self.inicializar_dominios()
            
            logger.info("✅ Banco inicializado com sucesso.")
        except Exception as e:
            logger.error(f"❌ Erro durante inicialização do banco: {e}", exc_info=True)
            raise


def inicializar_banco():
    """
    Função de conveniência para inicializar o banco.
    
    Esta função mantém compatibilidade com o código existente.
    """
    orchestrator = DatabaseOrchestrator()
    orchestrator.initialize()

