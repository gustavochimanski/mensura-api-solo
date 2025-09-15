# app/database/migrations/create_impressoras_table.py
"""
Script de migração para criar a tabela de impressoras
Execute este script para criar a tabela no banco de dados
"""

from sqlalchemy import text
from app.database.db_connection import engine

def create_impressoras_table():
    """Cria a tabela de impressoras no banco de dados"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS mensura.impressoras (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(100) NOT NULL,
        nome_impressora VARCHAR(100),
        fonte_nome VARCHAR(50) NOT NULL DEFAULT 'Courier New',
        fonte_tamanho INTEGER NOT NULL DEFAULT 24,
        espacamento_linha INTEGER NOT NULL DEFAULT 40,
        espacamento_item INTEGER NOT NULL DEFAULT 50,
        mensagem_rodape TEXT NOT NULL DEFAULT 'Obrigado pela preferencia!',
        formato_preco VARCHAR(50) NOT NULL DEFAULT 'R$ {:.2f}',
        formato_total VARCHAR(50) NOT NULL DEFAULT 'TOTAL: R$ {:.2f}',
        empresa_id INTEGER NOT NULL REFERENCES mensura.empresas(id) ON DELETE CASCADE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()
        print("Tabela 'impressoras' criada com sucesso!")

if __name__ == "__main__":
    create_impressoras_table()
