"""
Migração para adicionar status 'I' (PENDENTE_IMPRESSAO) ao enum pedido_status_enum
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    # Adiciona o novo valor 'I' ao enum existente
    op.execute("ALTER TYPE pedido_status_enum ADD VALUE 'I' AFTER 'P'")


def downgrade():
    # Não é possível remover valores de um enum em PostgreSQL
    # Esta migração não pode ser revertida automaticamente
    pass
