"""
Migration: Adicionar campos de auditoria ao PedidoStatusHistoricoModel

Esta migration adiciona novos campos de auditoria e índices para melhorar
a performance e rastreabilidade do histórico de status dos pedidos.

Data: 2024-12-19
Autor: Sistema
"""

from sqlalchemy import text

def upgrade(connection):
    """Aplicar as mudanças"""
    
    # Alterar coluna motivo para TEXT
    connection.execute(text("""
        ALTER TABLE delivery.pedido_status_historico_dv 
        ALTER COLUMN motivo TYPE TEXT;
    """))
    
    # Adicionar novas colunas
    connection.execute(text("""
        ALTER TABLE delivery.pedido_status_historico_dv 
        ADD COLUMN observacoes TEXT;
    """))
    
    connection.execute(text("""
        ALTER TABLE delivery.pedido_status_historico_dv 
        ADD COLUMN ip_origem VARCHAR(45);
    """))
    
    connection.execute(text("""
        ALTER TABLE delivery.pedido_status_historico_dv 
        ADD COLUMN user_agent VARCHAR(500);
    """))
    
    # Criar índices para performance
    connection.execute(text("""
        CREATE INDEX idx_hist_status 
        ON delivery.pedido_status_historico_dv (status);
    """))
    
    connection.execute(text("""
        CREATE INDEX idx_hist_criado_em 
        ON delivery.pedido_status_historico_dv (criado_em);
    """))
    
    connection.execute(text("""
        CREATE INDEX idx_hist_pedido_status 
        ON delivery.pedido_status_historico_dv (pedido_id, status);
    """))
    
    connection.execute(text("""
        CREATE INDEX idx_hist_pedido_criado_em 
        ON delivery.pedido_status_historico_dv (pedido_id, criado_em);
    """))


def downgrade(connection):
    """Reverter as mudanças"""
    
    # Remover índices
    connection.execute(text("""
        DROP INDEX IF EXISTS delivery.idx_hist_pedido_criado_em;
    """))
    
    connection.execute(text("""
        DROP INDEX IF EXISTS delivery.idx_hist_pedido_status;
    """))
    
    connection.execute(text("""
        DROP INDEX IF EXISTS delivery.idx_hist_criado_em;
    """))
    
    connection.execute(text("""
        DROP INDEX IF EXISTS delivery.idx_hist_status;
    """))
    
    # Remover colunas
    connection.execute(text("""
        ALTER TABLE delivery.pedido_status_historico_dv 
        DROP COLUMN IF EXISTS user_agent;
    """))
    
    connection.execute(text("""
        ALTER TABLE delivery.pedido_status_historico_dv 
        DROP COLUMN IF EXISTS ip_origem;
    """))
    
    connection.execute(text("""
        ALTER TABLE delivery.pedido_status_historico_dv 
        DROP COLUMN IF EXISTS observacoes;
    """))
    
    # Reverter coluna motivo para VARCHAR(255)
    connection.execute(text("""
        ALTER TABLE delivery.pedido_status_historico_dv 
        ALTER COLUMN motivo TYPE VARCHAR(255);
    """))


# Script para executar a migration
if __name__ == "__main__":
    from app.database.db_connection import engine
    
    with engine.connect() as conn:
        print("Aplicando migration: Adicionar campos de auditoria ao PedidoStatusHistoricoModel")
        upgrade(conn)
        conn.commit()
        print("Migration aplicada com sucesso!")
