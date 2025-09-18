# database/migrations/migrate_categorias_to_mensura.py
"""
Migration para mover categorias do delivery para mensura e ajustar relacionamentos
"""
from sqlalchemy import text
from app.database.db_connection import engine


def migrate_categorias_to_mensura():
    """Executa a migração das categorias para o schema mensura"""
    
    with engine.connect() as conn:
        # Iniciar transação
        trans = conn.begin()
        
        try:
            # 1. Criar tabela de categorias no schema mensura
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS mensura.categorias (
                    id SERIAL PRIMARY KEY,
                    descricao VARCHAR(100) NOT NULL,
                    ativo INTEGER NOT NULL DEFAULT 1,
                    parent_id INTEGER REFERENCES mensura.categorias(id) ON DELETE SET NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # 2. Migrar dados das categorias do delivery para mensura
            conn.execute(text("""
                INSERT INTO mensura.categorias (id, descricao, ativo, parent_id, created_at, updated_at)
                SELECT 
                    id,
                    descricao,
                    1 as ativo,
                    parent_id,
                    created_at,
                    updated_at
                FROM delivery.categoria_dv
                ON CONFLICT (id) DO NOTHING;
            """))
            
            # 3. Atualizar a coluna cod_categoria na tabela cadprod para ser nullable
            conn.execute(text("""
                ALTER TABLE mensura.cadprod 
                ALTER COLUMN cod_categoria DROP NOT NULL;
            """))
            
            # 4. Atualizar a foreign key para apontar para mensura.categorias
            conn.execute(text("""
                ALTER TABLE mensura.cadprod 
                DROP CONSTRAINT IF EXISTS cadprod_cod_categoria_fkey;
            """))
            
            conn.execute(text("""
                ALTER TABLE mensura.cadprod 
                ADD CONSTRAINT cadprod_cod_categoria_fkey 
                FOREIGN KEY (cod_categoria) REFERENCES mensura.categorias(id) ON DELETE RESTRICT;
            """))
            
            # 5. Atualizar sequência da tabela categorias para continuar do último ID
            conn.execute(text("""
                SELECT setval('mensura.categorias_id_seq', 
                    COALESCE((SELECT MAX(id) FROM mensura.categorias), 1), true);
            """))
            
            # Commit da transação
            trans.commit()
            print("✅ Migração executada com sucesso!")
            
        except Exception as e:
            # Rollback em caso de erro
            trans.rollback()
            print(f"❌ Erro na migração: {e}")
            raise


def rollback_categorias_migration():
    """Reverte a migração (para casos de emergência)"""
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            # Reverter foreign key para delivery
            conn.execute(text("""
                ALTER TABLE mensura.cadprod 
                DROP CONSTRAINT IF EXISTS cadprod_cod_categoria_fkey;
            """))
            
            conn.execute(text("""
                ALTER TABLE mensura.cadprod 
                ADD CONSTRAINT cadprod_cod_categoria_fkey 
                FOREIGN KEY (cod_categoria) REFERENCES delivery.categoria_dv(id) ON DELETE RESTRICT;
            """))
            
            # Tornar coluna NOT NULL novamente
            conn.execute(text("""
                ALTER TABLE mensura.cadprod 
                ALTER COLUMN cod_categoria SET NOT NULL;
            """))
            
            trans.commit()
            print("✅ Rollback executado com sucesso!")
            
        except Exception as e:
            trans.rollback()
            print(f"❌ Erro no rollback: {e}")
            raise


if __name__ == "__main__":
    migrate_categorias_to_mensura()
