from sqlalchemy import Column, String, Integer, Numeric, DateTime, func
from sqlalchemy.orm import relationship
from app.api.mensura.models.association_tables import entregador_empresa
from app.database.db_connection import Base

class EntregadorDeliveryModel(Base):
    __tablename__ = "entregadores_dv"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)

    telefone = Column(String(20), nullable=True)
    documento = Column(String(20), nullable=True)  # CPF/CNPJ
    veiculo_tipo = Column(String(20), nullable=True)  # moto, bike, carro
    placa = Column(String(10), nullable=True)

    acrescimo_taxa = Column(Numeric(10, 2), nullable=True, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    empresas = relationship("EmpresaModel", secondary=entregador_empresa, back_populates="entregadores")
    pedidos = relationship("PedidoDeliveryModel", back_populates="entregador")
