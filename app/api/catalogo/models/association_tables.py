# app/api/catalogo/models/association_tables.py
from sqlalchemy import (
    Table,
    Column,
    Integer,
    ForeignKey,
    UniqueConstraint,
    Index,
    DateTime,
    func,
    PrimaryKeyConstraint,
    String,
    Boolean,
    ForeignKeyConstraint,
    Numeric,
)
from app.database.db_connection import Base

# Tabela de associação Produto-Complemento
produto_complemento_link = Table(
    "produto_complemento_link",
    Base.metadata,
    Column("produto_id", Integer, ForeignKey("catalogo.produtos.id", ondelete="CASCADE"), primary_key=True),
    Column("complemento_id", Integer, ForeignKey("catalogo.complemento_produto.id", ondelete="CASCADE"), primary_key=True),
    Column("ordem", Integer, nullable=False, default=0),
    # Configurações específicas da vinculação (podem ser diferentes para cada produto)
    Column("obrigatorio", Boolean, nullable=False, default=False),
    Column("quantitativo", Boolean, nullable=False, default=False),
    Column("minimo_itens", Integer, nullable=True),
    Column("maximo_itens", Integer, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    schema="catalogo",
    info={"description": "Tabela de relacionamento N:N entre produtos e complementos"}
)

# Tabela de associação Receita-Complemento
receita_complemento_link = Table(
    "receita_complemento_link",
    Base.metadata,
    Column("receita_id", Integer, ForeignKey("catalogo.receitas.id", ondelete="CASCADE"), primary_key=True),
    Column("complemento_id", Integer, ForeignKey("catalogo.complemento_produto.id", ondelete="CASCADE"), primary_key=True),
    Column("ordem", Integer, nullable=False, default=0),
    # Configurações específicas da vinculação (podem ser diferentes para cada receita)
    Column("obrigatorio", Boolean, nullable=False, default=False),
    Column("quantitativo", Boolean, nullable=False, default=False),
    Column("minimo_itens", Integer, nullable=True),
    Column("maximo_itens", Integer, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    schema="catalogo",
    info={"description": "Tabela de relacionamento N:N entre receitas e complementos"}
)

# Tabela de associação Combo-Complemento
combo_complemento_link = Table(
    "combo_complemento_link",
    Base.metadata,
    Column("combo_id", Integer, ForeignKey("catalogo.combos.id", ondelete="CASCADE"), primary_key=True),
    Column("complemento_id", Integer, ForeignKey("catalogo.complemento_produto.id", ondelete="CASCADE"), primary_key=True),
    Column("ordem", Integer, nullable=False, default=0),
    # Configurações específicas da vinculação (podem ser diferentes para cada combo)
    Column("obrigatorio", Boolean, nullable=False, default=False),
    Column("quantitativo", Boolean, nullable=False, default=False),
    Column("minimo_itens", Integer, nullable=True),
    Column("maximo_itens", Integer, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    schema="catalogo",
    info={"description": "Tabela de relacionamento N:N entre combos e complementos"}
)

