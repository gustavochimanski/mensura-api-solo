# app/database/migrations/run_migrations.py
"""
Script para executar a migration de categorias/produtos
Execute este script a partir da raiz do projeto: python app/database/migrations/run_migrations.py
"""
import sys
import os

# Adicionar o diretório raiz do projeto ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)

from sqlalchemy import text
from app.database.db_connection import engine
from app.database.migrations.migrate_categorias_to_mensura import migrate_categorias_to_mensura

def check_migration_status():
    """Verifica o status da migration de categorias/produtos"""
    
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
        
        print("=== Status da Migration de Categorias/Produtos ===")
        print(f"✅ Tabela mensura.categorias existe: {categorias_exists}")
        print(f"✅ Foreign key correta em cadprod: {fk_correct}")
        
        return {
            'categorias_exists': categorias_exists,
            'fk_correct': fk_correct
        }

def run_pending_migrations():
    """Executa a migration de categorias/produtos"""
    
    print("🔍 Verificando status da migration...")
    status = check_migration_status()
    
    if not status['categorias_exists'] or not status['fk_correct']:
        print("\n🔄 Executando migration de categorias/produtos...")
        migrate_categorias_to_mensura()
    else:
        print("\n✅ Migration de categorias/produtos já executada")
    
    print("\n🔍 Verificando status final...")
    final_status = check_migration_status()
    
    if all(final_status.values()):
        print("\n✅ Migration de categorias/produtos executada com sucesso!")
    else:
        print("\n❌ A migration falhou. Verifique os logs acima.")

if __name__ == "__main__":
    run_pending_migrations()
