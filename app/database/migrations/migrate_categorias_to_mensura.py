# app/database/migrations/migrate_categorias_to_mensura.py
"""
Migration para criar a tabela de categorias no schema mensura e ajustar relacionamentos
"""
import sys
import os

# Adicionar o diretório raiz do projeto ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)

from sqlalchemy import text
from app.database.db_connection import engine

def migrate_categorias_to_mensura():
    """Executa a migração das categorias para o schema mensura"""
    
    with engine.connect() as conn:
        # Iniciar transação
        trans = conn.begin()
        
        try:
            print("🔄 Criando tabela mensura.categorias...")
            
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
            
            print("🔄 Verificando se existem dados para migrar...")
            
            # 2. Verificar se existem categorias no delivery para migrar
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'delivery' 
                    AND table_name = 'categoria_dv'
                );
            """))
            
            if result.scalar():
                print("🔄 Migrando dados das categorias do delivery para mensura...")
                
                # Migrar dados das categorias do delivery para mensura
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
                
                # Atualizar sequência da tabela categorias para continuar do último ID
                conn.execute(text("""
                    SELECT setval('mensura.categorias_id_seq', 
                        COALESCE((SELECT MAX(id) FROM mensura.categorias), 1), true);
                """))
            else:
                print("ℹ️ Tabela delivery.categoria_dv não encontrada, criando apenas a estrutura...")
                
                # Inserir algumas categorias padrão se não existirem
                conn.execute(text("""
                    INSERT INTO mensura.categorias (descricao, ativo) VALUES 
                    ('Geral', 1),
                    ('Bebidas', 1),
                    ('Comidas', 1)
                    ON CONFLICT DO NOTHING;
                """))
            
            print("🔄 Atualizando foreign key em cadprod...")
            
            # 3. Atualizar a coluna cod_categoria na tabela cadprod para ser nullable
            conn.execute(text("""
                ALTER TABLE mensura.cadprod 
                ALTER COLUMN cod_categoria DROP NOT NULL;
            """))
            
            # 4. Remover constraint antiga se existir
            conn.execute(text("""
                ALTER TABLE mensura.cadprod 
                DROP CONSTRAINT IF EXISTS cadprod_cod_categoria_fkey;
            """))
            
            # 5. Adicionar nova foreign key para apontar para mensura.categorias
            conn.execute(text("""
                ALTER TABLE mensura.cadprod 
                ADD CONSTRAINT cadprod_cod_categoria_fkey 
                FOREIGN KEY (cod_categoria) REFERENCES mensura.categorias(id) ON DELETE RESTRICT;
            """))
            
            # Commit da transação
            trans.commit()
            print("✅ Migração executada com sucesso!")
            print("🎉 Relacionamento entre ProdutoModel e CategoriaModel corrigido!")
            
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
            print("🔄 Revertendo migração...")
            
            # Remover foreign key atual
            conn.execute(text("""
                ALTER TABLE mensura.cadprod 
                DROP CONSTRAINT IF EXISTS cadprod_cod_categoria_fkey;
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
