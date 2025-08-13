# app/api/delivery/models/vitrine_dv_model.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from app.api.mensura.models.association_tables import VitrineCategoriaLink, VitrineProdutoEmpLink
from app.database.db_connection import Base

class VitrinesModel(Base):
    __tablename__ = "vitrines_dv"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True)

    # "P" = aparece na home, outros valores = não aparece
    tipo_exibicao = Column(String(1), nullable=True)

    titulo = Column(String(100), nullable=False)
    slug   = Column(String(100), nullable=False)  # avalie unique por empresa, se futuramente houver empresa_id
    ordem  = Column(Integer, nullable=False, default=1)

    # --- Relacionamentos N:N ---
    categorias = relationship(
        "CategoriaDeliveryModel",
        secondary=VitrineCategoriaLink.__table__,
        back_populates="vitrines",
        passive_deletes=True,
        order_by=VitrineCategoriaLink.posicao,
    )

    produtos_emp = relationship(
        "ProdutoEmpDeliveryModel",
        secondary="delivery.vitrine_prod_emp_dv",
        back_populates="vitrines",
        passive_deletes=True,
        # order_by=VitrineProdutoEmpLink.posicao,  # ative se quiser ordenar os produtos por 'posicao'
    )

    @hybrid_property
    def is_home(self) -> bool:
        return self.tipo_exibicao == "P"
