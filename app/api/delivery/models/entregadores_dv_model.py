from sqlalchemy import Column, String, Integer, ARRAY
from sqlalchemy.orm import relationship

from app.api.mensura.models.association_tables import entregador_empresa
from app.database.db_connection import Base


class EntregadorDeliveryModel(Base):
    __tablename__ = "entregadores_dv"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    acrescimo_taxa = Column(Integer)
    empresas = Column(ARRAY(Integer), nullable=False, default=list)

    empresas = relationship(
        "EmpresaModel",
        secondary=entregador_empresa,
        back_populates="entregadores"
    )

    # Relacionamentos
    pedidos = relationship("PedidoDeliveryModel", back_populates="entregador")
