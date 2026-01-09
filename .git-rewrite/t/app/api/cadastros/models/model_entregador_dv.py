from sqlalchemy import Column, String, Integer, Numeric, DateTime, func
from sqlalchemy.orm import relationship
from app.api.cadastros.models.association_tables import entregador_empresa
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class EntregadorDeliveryModel(Base):
    __tablename__ = "entregadores_dv"
    __table_args__ = {"schema": "cadastros"}

    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)

    telefone = Column(String(20), nullable=True)
    documento = Column(String(20), nullable=True)  # CPF/CNPJ
    veiculo_tipo = Column(String(20), nullable=True)  # moto, bike, carro
    placa = Column(String(10), nullable=True)

    acrescimo_taxa = Column(Numeric(10, 2), nullable=True, default=0)
    valor_diaria = Column(Numeric(10, 2), nullable=True)

    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed,  nullable=False)

    empresas = relationship("EmpresaModel", secondary=entregador_empresa, back_populates="entregadores")
    pedidos = relationship("PedidoDeliveryModel", back_populates="entregador")
