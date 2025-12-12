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
    Column("produto_cod_barras", String, ForeignKey("catalogo.produtos.cod_barras", ondelete="CASCADE"), primary_key=True),
    Column("complemento_id", Integer, ForeignKey("catalogo.complemento_produto.id", ondelete="CASCADE"), primary_key=True),
    Column("ordem", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    schema="catalogo",
    info={"description": "Tabela de relacionamento N:N entre produtos e complementos"}
)

# Tabela de associação N:N entre Complementos e Adicionais
# Permite que um adicional pertença a vários complementos e um complemento tenha vários adicionais
complemento_item_link = Table(
    "complemento_item_link",
    Base.metadata,
    Column("complemento_id", Integer, ForeignKey("catalogo.complemento_produto.id", ondelete="CASCADE"), primary_key=True),
    Column("item_id", Integer, ForeignKey("catalogo.adicionais.id", ondelete="CASCADE"), primary_key=True),
    Column("ordem", Integer, nullable=False, default=0),
    # Preço específico do item dentro deste complemento (override do preço padrão do adicional)
    Column("preco_complemento", Numeric(18, 2), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    schema="catalogo",
    info={"description": "Tabela de relacionamento N:N entre complementos e adicionais"}
)

# Tabela de associação Receita-Complemento
receita_complemento_link = Table(
    "receita_complemento_link",
    Base.metadata,
    Column("receita_id", Integer, ForeignKey("catalogo.receitas.id", ondelete="CASCADE"), primary_key=True),
    Column("complemento_id", Integer, ForeignKey("catalogo.complemento_produto.id", ondelete="CASCADE"), primary_key=True),
    Column("ordem", Integer, nullable=False, default=0),
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
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    schema="catalogo",
    info={"description": "Tabela de relacionamento N:N entre combos e complementos"}
)

# Tabela de associação Produto-Adicional (DEPRECADA - mantida para compatibilidade)
# Agora os adicionais estão dentro de complementos, então o relacionamento é Produto -> Complemento -> Adicionais
produto_adicional_link = Table(
    "produto_adicional_link",
    Base.metadata,
    Column("produto_cod_barras", String, ForeignKey("catalogo.produtos.cod_barras", ondelete="CASCADE"), primary_key=True),
    Column("adicional_id", Integer, ForeignKey("catalogo.adicionais.id", ondelete="CASCADE"), primary_key=True),
    Column("ordem", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    schema="catalogo",
    info={"description": "Tabela de relacionamento N:N entre produtos e adicionais (DEPRECADA - usar complementos)"}
)

