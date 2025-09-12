#!/usr/bin/env python3
"""
Script para executar a migration dos snapshots de endereço
"""

import logging
from sqlalchemy import text
from app.database.db_connection import engine

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def executar_migration():
    """Executa a migration para adicionar os campos de snapshot"""
    
    try:
        with engine.begin() as conn:
            logger.info("🔄 Iniciando migration para snapshots de endereço...")
            
            # 1. Verificar se a tabela existe
            check_table = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'delivery' 
                    AND table_name = 'pedidos_dv'
                );
            """)
            
            table_exists = conn.execute(check_table).scalar()
            if not table_exists:
                logger.error("❌ Tabela delivery.pedidos_dv não existe!")
                return False
            
            logger.info("✅ Tabela delivery.pedidos_dv encontrada")
            
            # 2. Adicionar campo endereco_snapshot
            logger.info("🔄 Adicionando campo endereco_snapshot...")
            conn.execute(text("""
                ALTER TABLE delivery.pedidos_dv 
                ADD COLUMN IF NOT EXISTS endereco_snapshot JSONB;
            """))
            
            # 3. Adicionar campo endereco_geo
            logger.info("🔄 Adicionando campo endereco_geo...")
            conn.execute(text("""
                ALTER TABLE delivery.pedidos_dv 
                ADD COLUMN IF NOT EXISTS endereco_geo GEOGRAPHY(POINT, 4326);
            """))
            
            # 4. Atualizar registros existentes
            logger.info("🔄 Atualizando registros existentes...")
            conn.execute(text("""
                UPDATE delivery.pedidos_dv 
                SET endereco_snapshot = '{}'::jsonb 
                WHERE endereco_snapshot IS NULL;
            """))
            
            # 5. Tornar endereco_snapshot obrigatório
            logger.info("🔄 Configurando endereco_snapshot como obrigatório...")
            conn.execute(text("""
                ALTER TABLE delivery.pedidos_dv 
                ALTER COLUMN endereco_snapshot SET NOT NULL;
            """))
            
            # 6. Criar índices
            logger.info("🔄 Criando índices...")
            
            # Índice GIN
            try:
                conn.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pedidos_endereco_snapshot_gin 
                    ON delivery.pedidos_dv USING gin (endereco_snapshot);
                """))
                logger.info("✅ Índice GIN criado")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao criar índice GIN: {e}")
            
            # Índice GiST
            try:
                conn.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pedidos_endereco_geo_gist 
                    ON delivery.pedidos_dv USING gist (endereco_geo);
                """))
                logger.info("✅ Índice GiST criado")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao criar índice GiST: {e}")
            
            logger.info("🎉 Migration concluída com sucesso!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Erro durante migration: {e}")
        return False

if __name__ == "__main__":
    success = executar_migration()
    if success:
        print("✅ Migration executada com sucesso!")
    else:
        print("❌ Migration falhou!")
        exit(1)
