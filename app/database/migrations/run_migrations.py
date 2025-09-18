# app/database/migrations/run_migrations.py
"""
Script para executar todas as migrations pendentes
"""
import sys
import os

# Adicionar o diretório raiz do projeto ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import text
from app.database.db_connection import engine
from app.database.migrations.migrate_categorias_to_mensura import migrate_categorias_to_mensura
from app.database.migrations.create_impressoras_table import create_impressoras_table

def check_migration_status():
    """Verifica o status das migrations"""
    
    with engine.connect() as conn:
        # Verifica se a tabela mensura.categorias existe
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'mensura' 
                AND table_name = 'categorias'
            );
        """))
        categorias_exists = result.scalar()
        
        # Verifica se a tabela mensura.impressoras existe
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'mensura' 
                AND table_name = 'impressoras'
            );
        """))
        impressoras_exists = result.scalar()
        
        # Verifica se a foreign key está apontando para mensura.categorias
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
            WHERE tc.table_schema = 'mensura' 
            AND tc.table_name = 'cadprod'
            AND tc.constraint_type = 'FOREIGN KEY'
            AND ccu.table_schema = 'mensura'
            AND ccu.table_name = 'categorias';
        """))
        fk_correct = result.scalar() > 0
        
        print("=== Status das Migrations ===")
        print(f"✅ Tabela mensura.categorias existe: {categorias_exists}")
        print(f"✅ Tabela mensura.impressoras existe: {impressoras_exists}")
        print(f"✅ Foreign key correta em cadprod: {fk_correct}")
        
        return {
            'categorias_exists': categorias_exists,
            'impressoras_exists': impressoras_exists,
            'fk_correct': fk_correct
        }

def run_pending_migrations():
    """Executa as migrations pendentes"""
    
    print("🔍 Verificando status das migrations...")
    status = check_migration_status()
    
    if not status['categorias_exists'] or not status['fk_correct']:
        print("\n🔄 Executando migration de categorias...")
        migrate_categorias_to_mensura()
    else:
        print("\n✅ Migration de categorias já executada")
    
    if not status['impressoras_exists']:
        print("\n🔄 Executando migration de impressoras...")
        create_impressoras_table()
    else:
        print("\n✅ Migration de impressoras já executada")
    
    print("\n🔍 Verificando status final...")
    final_status = check_migration_status()
    
    if all(final_status.values()):
        print("\n✅ Todas as migrations foram executadas com sucesso!")
    else:
        print("\n❌ Algumas migrations falharam. Verifique os logs acima.")

if __name__ == "__main__":
    run_pending_migrations()
