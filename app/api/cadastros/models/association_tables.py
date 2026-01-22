# app/api/cadastros/models/association_tables.py
from sqlalchemy import Table, Column, Integer, ForeignKey, UniqueConstraint, Index, DateTime, func, \
    PrimaryKeyConstraint, String, Boolean, ForeignKeyConstraint
from app.database.db_connection import Base
# Nota: produto_adicional_link foi removido - adicionais agora são vínculos de produtos/receitas/combos em complementos

# Tabela de associação entregador-empresa
entregador_empresa = Table(
    "entregador_empresa",
    Base.metadata,
    Column("entregador_id", Integer, ForeignKey("cadastros.entregadores_dv.id", ondelete="CASCADE")),
    Column("empresa_id", Integer, ForeignKey("cadastros.empresas.id", ondelete="CASCADE")),
    schema="cadastros",
)

# Tabela de associação usuario-empresa
usuario_empresa = Table(
    "usuario_empresa",
    Base.metadata,
    Column("usuario_id", Integer, ForeignKey("cadastros.usuarios.id", ondelete="CASCADE")),
    Column("empresa_id", Integer, ForeignKey("cadastros.empresas.id", ondelete="CASCADE")),
    schema="cadastros",
)

# Classe de associação Vitrine-Categoria
class VitrineCategoriaLink(Base):
    __tablename__ = "vitrine_categoria_dv"

    __table_args__ = (
        UniqueConstraint("vitrine_id", "categoria_id", name="uq_vitrine_categoria"),
        Index("idx_vitcat_categoria", "categoria_id"),
        {"schema": "cardapio"},
    )
    id = Column(Integer, primary_key=True)
    vitrine_id = Column(Integer, ForeignKey("cardapio.vitrines_dv.id", ondelete="CASCADE"), nullable=False)
    categoria_id = Column(Integer, ForeignKey("cardapio.categoria_dv.id", ondelete="CASCADE"), nullable=False)
    posicao = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# Classe de associação Vitrine-Produto (global, sem separação por empresa)
class VitrineProdutoLink(Base):
    """
    Liga Produto (cod_barras) a vitrines (N:N) com ordenação.
    Vitrines agora são globais, não mais separadas por empresa.
    """
    __tablename__ = "vitrine_produto"
    __table_args__ = (
        PrimaryKeyConstraint("vitrine_id", "cod_barras", name="pk_vitrine_produto"),
        # FK para o produto base
        ForeignKeyConstraint(
            ["cod_barras"],
            ["catalogo.produtos.cod_barras"],
            ondelete="CASCADE",
        ),
        # FK simples para a vitrine
        ForeignKeyConstraint(
            ["vitrine_id"],
            ["cardapio.vitrines_dv.id"],
            ondelete="CASCADE",
        ),
        Index("idx_vitprod_vitrine", "vitrine_id"),
        Index("idx_vitprod_cod_barras", "cod_barras"),
        {"schema": "cardapio"},
    )

    vitrine_id  = Column(Integer, nullable=False)
    cod_barras  = Column(String,  nullable=False)

    posicao     = Column(Integer, nullable=False, default=0)
    destaque    = Column(Boolean, nullable=False, default=False)

    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# Classe de associação Vitrine-Combo
class VitrineComboLink(Base):
    """
    Liga Combos a vitrines (N:N) com ordenação.
    """
    __tablename__ = "vitrine_combo"
    __table_args__ = (
        PrimaryKeyConstraint("vitrine_id", "combo_id", name="pk_vitrine_combo"),
        ForeignKeyConstraint(
            ["combo_id"],
            ["catalogo.combos.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["vitrine_id"],
            ["cardapio.vitrines_dv.id"],
            ondelete="CASCADE",
        ),
        Index("idx_vitcombo_vitrine", "vitrine_id"),
        Index("idx_vitcombo_combo", "combo_id"),
        {"schema": "cardapio"},
    )

    vitrine_id = Column(Integer, nullable=False)
    combo_id = Column(Integer, nullable=False)
    posicao = Column(Integer, nullable=False, default=0)
    destaque = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# Classe de associação Vitrine-Receita
class VitrineReceitaLink(Base):
    """
    Liga Receitas a vitrines (N:N) com ordenação.
    Receitas estão no schema cadastros.
    """
    __tablename__ = "vitrine_receita"
    __table_args__ = (
        PrimaryKeyConstraint("vitrine_id", "receita_id", name="pk_vitrine_receita"),
        ForeignKeyConstraint(
            ["receita_id"],
            ["catalogo.receitas.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["vitrine_id"],
            ["cardapio.vitrines_dv.id"],
            ondelete="CASCADE",
        ),
        Index("idx_vitreceita_vitrine", "vitrine_id"),
        Index("idx_vitreceita_receita", "receita_id"),
        {"schema": "cardapio"},
    )

    vitrine_id = Column(Integer, nullable=False)
    receita_id = Column(Integer, nullable=False)
    posicao = Column(Integer, nullable=False, default=0)
    destaque = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)