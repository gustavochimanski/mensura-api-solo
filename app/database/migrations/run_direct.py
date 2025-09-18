#!/usr/bin/env python3
"""
Script para executar a migration diretamente do diretório migrations
Execute: python run_direct.py
"""
import sys
import os

# Adicionar o diretório raiz do projeto ao path
# Este script deve ser executado de: /usr/src/app/app/database/migrations/
# O projeto root está em: /usr/src/app/
project_root = "/usr/src/app"
sys.path.insert(0, project_root)

try:
    # Executar a migration específica para corrigir a foreign key
    print("🔄 Executando correção da foreign key de categorias...")
    
    # Importar e executar a migration
    from fix_categoria_fk import fix_categoria_foreign_key
    fix_categoria_foreign_key()
    
except Exception as e:
    print(f"❌ Erro ao executar migration: {e}")
    sys.exit(1)
