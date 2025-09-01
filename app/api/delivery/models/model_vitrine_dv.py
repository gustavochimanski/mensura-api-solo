# app/api/delivery/models/model_vitrine_dv.py
from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
#
from app.api.mensura.models.association_tables import VitrineCategoriaLink, VitrineProdutoEmpLink
from app.database.db_connection import Base

class VitrinesModel(Base):
    __tablename__ = "vitrines_dv"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_vitrine_slug_global"),  # 🔒 único global
        {"schema": "delivery"},
    )

    id = Column(Integer, primary_key=True)
    tipo_exibicao = Column(String(1), nullable=True)
    titulo = Column(String(100), nullable=False)
    slug   = Column(String(100), nullable=False)  # agora com unique via table_args
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
        "ProdutoEmpModel",
        secondary=VitrineProdutoEmpLink.__table__,  # 👈 em vez de string
        back_populates="vitrines",
        passive_deletes=True
    )

    @hybrid_property
    def is_home(self) -> bool:
        return self.tipo_exibicao == "P"
