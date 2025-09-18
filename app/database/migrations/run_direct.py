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
    # Executar a migration diretamente
    print("🔄 Executando migration de categorias/produtos...")
    
    # Importar e executar a migration
    from migrate_categorias_to_mensura import migrate_categorias_to_mensura
    migrate_categorias_to_mensura()
    
except Exception as e:
    print(f"❌ Erro ao executar migration: {e}")
    sys.exit(1)
