#!/usr/bin/env python3
"""
Script para adicionar o valor 'I' ao enum pedido_status_enum existente
"""

from app.database.db_connection import engine
from sqlalchemy import text

def fix_enum():
    try:
        with engine.connect() as conn:
            # Primeiro, verificar se o enum existe e quais valores tem
            result = conn.execute(text("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (
                    SELECT oid 
                    FROM pg_type 
                    WHERE typname = 'pedido_status_enum'
                )
                ORDER BY enumsortorder;
            """))
            
            print('Valores atuais do enum pedido_status_enum:')
            values = []
            for row in result:
                values.append(row[0])
                print(f'  - {row[0]}')
            
            if not values:
                print('❌ Enum pedido_status_enum não encontrado!')
                return False
            
            if 'I' in values:
                print('✅ Valor "I" já existe no enum!')
                return True
            
            # Adicionar o valor 'I' ao enum existente
            print('🔧 Adicionando valor "I" ao enum...')
            conn.execute(text("ALTER TYPE pedido_status_enum ADD VALUE 'I' AFTER 'P'"))
            conn.commit()
            
            print('✅ Valor "I" adicionado com sucesso!')
            
            # Verificar novamente
            result = conn.execute(text("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (
                    SELECT oid 
                    FROM pg_type 
                    WHERE typname = 'pedido_status_enum'
                )
                ORDER BY enumsortorder;
            """))
            
            print('Valores do enum após a correção:')
            for row in result:
                print(f'  - {row[0]}')
            
            return True
            
    except Exception as e:
        print(f'❌ Erro ao corrigir enum: {e}')
        return False

if __name__ == "__main__":
    fix_enum()
