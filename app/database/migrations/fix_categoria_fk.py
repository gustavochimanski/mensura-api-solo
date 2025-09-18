# app/database/migrations/fix_categoria_fk.py
"""
Migration específica para corrigir a foreign key de cod_categoria
"""
import sys
import os

# Adicionar o diretório raiz do projeto ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)

from sqlalchemy import text
from app.database.db_connection import engine

def fix_categoria_foreign_key():
    """Corrige a foreign key de cod_categoria para apontar para mensura.categorias"""
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            print("🔍 Verificando estado atual da foreign key...")
            
            # Verificar qual foreign key está ativa
            result = conn.execute(text("""
                SELECT 
                    tc.constraint_name,
                    ccu.table_schema as referenced_schema,
                    ccu.table_name as referenced_table
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu 
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_schema = 'mensura' 
                AND tc.table_name = 'cadprod'
                AND tc.constraint_type = 'FOREIGN KEY'
                AND ccu.column_name = 'cod_categoria';
            """))
            
            current_fk = result.fetchone()
            if current_fk:
                print(f"📋 Foreign key atual: {current_fk.constraint_name}")
                print(f"📋 Referencia: {current_fk.referenced_schema}.{current_fk.referenced_table}")
            else:
                print("⚠️ Nenhuma foreign key encontrada para cod_categoria")
            
            print("🔄 Criando tabela mensura.categorias se não existir...")
            
            # 1. Garantir que a tabela mensura.categorias existe
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
            
            print("🔄 Inserindo categorias padrão se não existirem...")
            
            # 2. Inserir categorias padrão
            conn.execute(text("""
                INSERT INTO mensura.categorias (descricao, ativo) VALUES 
                ('Geral', 1),
                ('Bebidas', 1),
                ('Comidas', 1),
                ('Sobremesas', 1),
                ('Lanches', 1)
                ON CONFLICT DO NOTHING;
            """))
            
            print("🔄 Removendo foreign key antiga...")
            
            # 3. Remover todas as constraints de foreign key existentes
            conn.execute(text("""
                ALTER TABLE mensura.cadprod 
                DROP CONSTRAINT IF EXISTS cadprod_cod_categoria_fkey;
            """))
            
            conn.execute(text("""
                ALTER TABLE mensura.cadprod 
                DROP CONSTRAINT IF EXISTS fk_cadprod_categoria;
            """))
            
            # 4. Tornar a coluna nullable temporariamente
            print("🔄 Tornando coluna cod_categoria nullable...")
            conn.execute(text("""
                ALTER TABLE mensura.cadprod 
                ALTER COLUMN cod_categoria DROP NOT NULL;
            """))
            
            print("🔄 Adicionando nova foreign key para mensura.categorias...")
            
            # 5. Adicionar nova foreign key
            conn.execute(text("""
                ALTER TABLE mensura.cadprod 
                ADD CONSTRAINT cadprod_cod_categoria_fkey 
                FOREIGN KEY (cod_categoria) REFERENCES mensura.categorias(id) ON DELETE RESTRICT;
            """))
            
            print("🔄 Atualizando produtos sem categoria...")
            
            # 6. Atualizar produtos que não têm categoria para usar categoria "Geral" (id=1)
            conn.execute(text("""
                UPDATE mensura.cadprod 
                SET cod_categoria = 1 
                WHERE cod_categoria IS NULL;
            """))
            
            print("🔍 Verificando nova foreign key...")
            
            # Verificar se a nova foreign key foi criada
            result = conn.execute(text("""
                SELECT 
                    tc.constraint_name,
                    ccu.table_schema as referenced_schema,
                    ccu.table_name as referenced_table
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu 
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_schema = 'mensura' 
                AND tc.table_name = 'cadprod'
                AND tc.constraint_type = 'FOREIGN KEY'
                AND ccu.column_name = 'cod_categoria';
            """))
            
            new_fk = result.fetchone()
            if new_fk:
                print(f"✅ Nova foreign key criada: {new_fk.constraint_name}")
                print(f"✅ Agora referencia: {new_fk.referenced_schema}.{new_fk.referenced_table}")
            else:
                print("❌ Falha ao criar nova foreign key")
            
            trans.commit()
            print("✅ Foreign key corrigida com sucesso!")
            print("🎉 Agora cod_categoria referencia mensura.categorias!")
            
        except Exception as e:
            trans.rollback()
            print(f"❌ Erro ao corrigir foreign key: {e}")
            raise

if __name__ == "__main__":
    fix_categoria_foreign_key()
