"""
Script simplificado para executar migrations do banco de dados

Este script executa as migrations diretamente sem importações complexas.

Uso:
    python app/database/migrations/run_migrations_simple.py
"""

import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.database.db_connection import engine
from sqlalchemy import text

def upgrade_001(connection):
    """Aplicar migration 001: Adicionar campos de auditoria ao PedidoStatusHistoricoModel"""
    
    print("📦 Executando migration 001: Adicionar campos de auditoria...")
    
    # Alterar coluna motivo para TEXT
    connection.execute(text("""
        ALTER TABLE delivery.pedido_status_historico_dv 
        ALTER COLUMN motivo TYPE TEXT;
    """))
    print("  ✅ Coluna motivo alterada para TEXT")
    
    # Adicionar novas colunas
    connection.execute(text("""
        ALTER TABLE delivery.pedido_status_historico_dv 
        ADD COLUMN IF NOT EXISTS observacoes TEXT;
    """))
    print("  ✅ Coluna observacoes adicionada")
    
    connection.execute(text("""
        ALTER TABLE delivery.pedido_status_historico_dv 
        ADD COLUMN IF NOT EXISTS ip_origem VARCHAR(45);
    """))
    print("  ✅ Coluna ip_origem adicionada")
    
    connection.execute(text("""
        ALTER TABLE delivery.pedido_status_historico_dv 
        ADD COLUMN IF NOT EXISTS user_agent VARCHAR(500);
    """))
    print("  ✅ Coluna user_agent adicionada")
    
    # Criar índices para performance
    try:
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_hist_status 
            ON delivery.pedido_status_historico_dv (status);
        """))
        print("  ✅ Índice idx_hist_status criado")
    except Exception as e:
        print(f"  ⚠️ Índice idx_hist_status já existe ou erro: {e}")
    
    try:
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_hist_criado_em 
            ON delivery.pedido_status_historico_dv (criado_em);
        """))
        print("  ✅ Índice idx_hist_criado_em criado")
    except Exception as e:
        print(f"  ⚠️ Índice idx_hist_criado_em já existe ou erro: {e}")
    
    try:
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_hist_pedido_status 
            ON delivery.pedido_status_historico_dv (pedido_id, status);
        """))
        print("  ✅ Índice idx_hist_pedido_status criado")
    except Exception as e:
        print(f"  ⚠️ Índice idx_hist_pedido_status já existe ou erro: {e}")
    
    try:
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_hist_pedido_criado_em 
            ON delivery.pedido_status_historico_dv (pedido_id, criado_em);
        """))
        print("  ✅ Índice idx_hist_pedido_criado_em criado")
    except Exception as e:
        print(f"  ⚠️ Índice idx_hist_pedido_criado_em já existe ou erro: {e}")

def run_migrations():
    """Executa todas as migrations em ordem"""
    
    print("🚀 Iniciando execução das migrations...")
    
    with engine.connect() as conn:
        try:
            upgrade_001(conn)
            conn.commit()
            print("🎉 Migration executada com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro ao executar migration: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    run_migrations()
