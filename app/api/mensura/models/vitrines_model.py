# app/models/mensura/vitrines_model.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.api.mensura.models.cad_prod_emp_delivery_model import ProdutosEmpDeliveryModel


class VitrinesModel(Base):
    __tablename__ = "vitrines"
    __table_args__ = {"schema": "mensura"}

    id = Column(Integer, primary_key=True)
    cod_empresa = Column(Integer, ForeignKey("mensura.empresas.id"), nullable=False)

    empresa_rel = relationship("EmpresaModel", back_populates="vitrines")

    cod_categoria = Column(
        Integer,
        ForeignKey("mensura.categoria_delivery.id", ondelete="CASCADE"),
        nullable=False,
    )

    titulo = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)
    ordem = Column(Integer, nullable=False)

    # Relacionamento reverso para Categoria
    categoria = relationship("CategoriaDeliveryModel", back_populates="vitrines")


    produtos = relationship(
        "ProdutosEmpDeliveryModel",
        back_populates="vitrine",
        foreign_keys=[ProdutosEmpDeliveryModel.vitrine_id]  # ✅ lista real
    )
