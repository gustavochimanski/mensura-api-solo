# app/models/vitrine_dv_model.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.api.delivery.models.cadprod_emp_dv_model import ProdutoEmpDeliveryModel


class VitrinesModel(Base):
    __tablename__ = "vitrines_dv"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True)

    cod_categoria = Column(
        String,
        ForeignKey("delivery.categoria_dv.id", ondelete="CASCADE"),
        nullable=False,
    )

    titulo = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)
    ordem = Column(Integer, nullable=False, default=1)

    # Relacionamento reverso para Categoria
    categoria = relationship("CategoriaDeliveryModel", back_populates="vitrines_dv")

    produtos_emp = relationship(
        "ProdutoEmpDeliveryModel",
        back_populates="vitrine",
        foreign_keys=[ProdutoEmpDeliveryModel.vitrine_id]  # ✅ lista real
    )
