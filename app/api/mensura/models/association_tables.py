# app/api/mensura/models/association_tables.py
from sqlalchemy import Table, Column, Integer, ForeignKey, UniqueConstraint, Index, DateTime, func, \
    PrimaryKeyConstraint, String, Boolean, ForeignKeyConstraint
from app.database.db_connection import Base
#
entregador_empresa = Table(
    "entregador_empresa",
    Base.metadata,
    Column("entregador_id", Integer, ForeignKey("delivery.entregadores_dv.id", ondelete="CASCADE")),
    Column("empresa_id", Integer, ForeignKey("mensura.empresas.id", ondelete="CASCADE")),
    schema="delivery",
)

usuario_empresa = Table(
    "usuario_empresa",
    Base.metadata,
    Column("usuario_id", Integer, ForeignKey("mensura.usuarios.id", ondelete="CASCADE")),
    Column("empresa_id", Integer, ForeignKey("mensura.empresas.id", ondelete="CASCADE")),
    schema="mensura",
)


class VitrineCategoriaLink(Base):
    __tablename__ = "vitrine_categoria_dv"
    __table_args__ = (
        UniqueConstraint("vitrine_id", "categoria_id", name="uq_vitrine_categoria"),
        Index("idx_vitcat_categoria", "categoria_id"),
        {"schema": "delivery"},
    )
    id = Column(Integer, primary_key=True)
    vitrine_id = Column(Integer, ForeignKey("delivery.vitrines_dv.id", ondelete="CASCADE"), nullable=False)
    categoria_id = Column(Integer, ForeignKey("delivery.categoria_dv.id", ondelete="CASCADE"), nullable=False)
    posicao = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class VitrineProdutoEmpLink(Base):
    """
    Liga ProdutoEmpDelivery (empresa_id + cod_barras) a vitrines (N:N) com ordenação.
    """
    __tablename__ = "vitrine_prod_emp"
    __table_args__ = (
        PrimaryKeyConstraint("vitrine_id", "empresa_id", "cod_barras", name="pk_vitrine_prod_emp"),
        # 🔧 CHAVE ESTRANGEIRA COMPOSTA → cadprod_emp_dv (não para cadprod_dv / empresas isoladamente)
        ForeignKeyConstraint(
            ["empresa_id", "cod_barras"],
            ["mensura.cadprod_emp.empresa_id", "mensura.cadprod_emp.cod_barras"],
            ondelete="CASCADE",
        ),
        # FK simples para a vitrine
        ForeignKeyConstraint(
            ["vitrine_id"],
            ["delivery.vitrines_dv.id"],
            ondelete="CASCADE",
        ),
        Index("idx_vitprod_vitrine", "vitrine_id"),
        Index("idx_vitprod_emp_prod", "empresa_id", "cod_barras"),
        {"schema": "delivery"},
    )

    vitrine_id  = Column(Integer, nullable=False)
    empresa_id  = Column(Integer, nullable=False)
    cod_barras  = Column(String,  nullable=False)

    posicao     = Column(Integer, nullable=False, default=0)
    destaque    = Column(Boolean, nullable=False, default=False)

    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)