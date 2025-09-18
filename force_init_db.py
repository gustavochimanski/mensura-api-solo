#!/usr/bin/env python3
"""
Script para forçar a inicialização do banco de dados
"""
import sys
import os

# Adicionar o diretório do projeto ao path
sys.path.append(os.path.dirname(__file__))

try:
    from app.database.init_db import (
        ensure_unaccent, 
        ensure_postgis, 
        criar_schemas, 
        criar_tabelas, 
        criar_usuario_admin_padrao
    )
    
    print("🔄 Forçando inicialização do banco de dados...")
    
    print("🔹 Instalando extensões...")
    ensure_unaccent()
    ensure_postgis()
    
    print("🔹 Criando schemas...")
    criar_schemas()
    
    print("🔹 Criando tabelas...")
    criar_tabelas()
    
    print("🔹 Garantindo usuário admin padrão...")
    criar_usuario_admin_padrao()
    
    print("✅ Banco inicializado com sucesso!")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
