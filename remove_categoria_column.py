#!/usr/bin/env python3
"""
Script para remover a coluna cod_categoria da tabela cadprod
"""
import sys
import os

# Adicionar o diretório do projeto ao path
sys.path.append(os.path.dirname(__file__))

try:
    from sqlalchemy import text
    from app.database.db_connection import engine
    
    print("🔄 Removendo coluna cod_categoria da tabela cadprod...")
    
    with engine.connect() as conn:
        # Verificar se a coluna existe
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'mensura' 
                AND table_name = 'cadprod'
                AND column_name = 'cod_categoria'
            );
        """))
        
        if result.scalar():
            print("✅ Coluna cod_categoria encontrada")
            
            # Remover foreign key primeiro
            print("🔄 Removendo foreign key...")
            conn.execute(text("""
                ALTER TABLE mensura.cadprod 
                DROP CONSTRAINT IF EXISTS cadprod_cod_categoria_fkey;
            """))
            
            # Remover a coluna
            print("🔄 Removendo coluna cod_categoria...")
            conn.execute(text("""
                ALTER TABLE mensura.cadprod 
                DROP COLUMN IF EXISTS cod_categoria;
            """))
            
            conn.commit()
            print("✅ Coluna cod_categoria removida com sucesso!")
        else:
            print("ℹ️ Coluna cod_categoria não existe")
        
        # Verificar se foi removida
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'mensura' 
                AND table_name = 'cadprod'
                AND column_name = 'cod_categoria'
            );
        """))
        
        if not result.scalar():
            print("✅ Confirmação: Coluna cod_categoria foi removida")
        else:
            print("❌ Erro: Coluna ainda existe")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
