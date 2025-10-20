"""
Script para executar migrations do banco de dados

Este script executa as migrations na ordem correta para manter
a consistência do banco de dados.

Uso:
    python app/database/migrations/run_migrations.py
"""

import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.database.db_connection import engine
from app.database.migrations.migration_001_add_audit_fields_to_pedido_status_historico import upgrade as upgrade_001

def run_migrations():
    """Executa todas as migrations em ordem"""
    
    migrations = [
        ("001_add_audit_fields_to_pedido_status_historico", upgrade_001),
    ]
    
    print("🚀 Iniciando execução das migrations...")
    
    with engine.connect() as conn:
        try:
            for migration_name, upgrade_func in migrations:
                print(f"📦 Executando migration: {migration_name}")
                upgrade_func(conn)
                conn.commit()
                print(f"✅ Migration {migration_name} executada com sucesso!")
            
            print("🎉 Todas as migrations foram executadas com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro ao executar migrations: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    run_migrations()
