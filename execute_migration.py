#!/usr/bin/env python3
"""
Script para executar a migration de categorias
"""
import sys
import os

# Adicionar o diretório do projeto ao path
sys.path.append(os.path.dirname(__file__))

try:
    from app.database.migrations.fix_categoria_fk import fix_categoria_foreign_key
    
    print("🔄 Executando migration para corrigir foreign key...")
    fix_categoria_foreign_key()
    print("✅ Migration executada com sucesso!")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
