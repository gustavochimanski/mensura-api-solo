from pydantic import ConfigDict
from sqlalchemy import (
    Column, Integer, String, Numeric, ForeignKey, Index, Boolean, DateTime, func
)
from sqlalchemy.orm import relationship
from app.database.db_connection import Base

class ProdutoEmpDeliveryModel(Base):
    __tablename__ = "cadprod_emp_dv"
    __table_args__ = (
        Index("idx_empresa_produto", "empresa_id", "cod_barras"),
        {"schema": "delivery"}
    )

    # PK composta (empresa + produto)
    empresa_id  = Column(Integer, ForeignKey("mensura.empresas.id", ondelete="RESTRICT"), primary_key=True)
    cod_barras  = Column(String, ForeignKey("delivery.cadprod_dv.cod_barras", ondelete="CASCADE"), primary_key=True, nullable=False)

    vitrine_id  = Column(Integer, ForeignKey("delivery.vitrines_dv.id", ondelete="SET NULL"), nullable=True)

    sku_empresa = Column(String(60), nullable=True)
    custo       = Column(Numeric(18, 5), nullable=True)
    preco_venda = Column(Numeric(18, 2), nullable=False)
    disponivel  = Column(Boolean, nullable=False, default=True)

    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    produto  = relationship("ProdutoDeliveryModel", back_populates="produtos_empresa")
    empresa  = relationship("EmpresaModel", back_populates="produtos_emp")
    vitrine  = relationship("VitrinesModel", back_populates="produtos_emp", foreign_keys=[vitrine_id])

    model_config = ConfigDict(from_attributes=True)
