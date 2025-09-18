#!/usr/bin/env python3
"""
Script para verificar e corrigir a foreign key de categorias
"""
import sys
import os

# Adicionar o diretório do projeto ao path
sys.path.append(os.path.dirname(__file__))

try:
    from sqlalchemy import text
    from app.database.db_connection import engine
    
    print("🔍 Verificando estado atual da foreign key...")
    
    with engine.connect() as conn:
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
            
            if current_fk.referenced_schema == 'delivery' and current_fk.referenced_table == 'categoria_dv':
                print("❌ PROBLEMA: Foreign key está apontando para delivery.categoria_dv")
                print("🔄 Corrigindo para mensura.categorias...")
                
                # Remover foreign key antiga
                conn.execute(text(f"""
                    ALTER TABLE mensura.cadprod 
                    DROP CONSTRAINT IF EXISTS {current_fk.constraint_name};
                """))
                
                # Adicionar nova foreign key
                conn.execute(text("""
                    ALTER TABLE mensura.cadprod 
                    ADD CONSTRAINT cadprod_cod_categoria_fkey 
                    FOREIGN KEY (cod_categoria) REFERENCES mensura.categorias(id) ON DELETE RESTRICT;
                """))
                
                conn.commit()
                print("✅ Foreign key corrigida!")
                
            elif current_fk.referenced_schema == 'mensura' and current_fk.referenced_table == 'categorias':
                print("✅ Foreign key já está correta!")
            else:
                print(f"⚠️ Foreign key inesperada: {current_fk.referenced_schema}.{current_fk.referenced_table}")
        else:
            print("⚠️ Nenhuma foreign key encontrada para cod_categoria")
            
            # Verificar se a tabela categorias existe
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'mensura' 
                    AND table_name = 'categorias'
                );
            """))
            
            if result.scalar():
                print("✅ Tabela mensura.categorias existe")
                print("🔄 Criando foreign key...")
                
                conn.execute(text("""
                    ALTER TABLE mensura.cadprod 
                    ADD CONSTRAINT cadprod_cod_categoria_fkey 
                    FOREIGN KEY (cod_categoria) REFERENCES mensura.categorias(id) ON DELETE RESTRICT;
                """))
                
                conn.commit()
                print("✅ Foreign key criada!")
            else:
                print("❌ Tabela mensura.categorias não existe!")
        
        # Verificar novamente
        print("\n🔍 Verificação final...")
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
        
        final_fk = result.fetchone()
        if final_fk:
            print(f"✅ Foreign key final: {final_fk.constraint_name}")
            print(f"✅ Agora referencia: {final_fk.referenced_schema}.{final_fk.referenced_table}")
        else:
            print("❌ Ainda não há foreign key")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
