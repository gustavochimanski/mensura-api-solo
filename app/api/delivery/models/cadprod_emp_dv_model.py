from pydantic import ConfigDict
from sqlalchemy import (
    Column, Integer, String, Numeric,
    ForeignKey, ForeignKeyConstraint,
    Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database.db_connection import Base

class ProdutoEmpDeliveryModel(Base):
    __tablename__ = "cadprod_emp_dv"
    __table_args__ = (
        ForeignKeyConstraint(["cod_barras"],["delivery.cadprod_dv.cod_barras"], name="fk_produto_empresa_cod_barras", ondelete="CASCADE"),
        UniqueConstraint("empresa_id", "cod_barras", name="uix_empresa_cod_barras"),
        Index("idx_empresa_produto", "empresa_id", "cod_barras"),
        {"schema": "delivery"}
    )

    # FK
    empresa_id  = Column(Integer, ForeignKey("mensura.empresas.id"), primary_key=True)
    cod_barras  = Column(String, ForeignKey("delivery.cadprod_dv.cod_barras"), primary_key=True, nullable=False)
    vitrine_id = Column(Integer, ForeignKey("delivery.vitrines_dv.id", ondelete="SET NULL"), nullable=True)

    custo = Column(Numeric(18, 5), nullable=True)
    preco_venda = Column(Numeric(18, 5), nullable=False)

    # Relacionamentos
    produto  = relationship("ProdutoDeliveryModel", back_populates="produtos_empresa")
    empresa  = relationship("EmpresaModel", back_populates="produtos_emp")
    vitrine  = relationship("VitrinesModel", back_populates="produtos_emp", foreign_keys=[vitrine_id])

    model_config = ConfigDict(from_attributes=True)
