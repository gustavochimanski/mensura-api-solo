from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from datetime import datetime
from pydantic import ConfigDict


class PedidoDeliveryModel(Base):
    __tablename__ = "pedidos_dv"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id = Column(Integer, ForeignKey("delivery.clientes_dv.id", ondelete="SET NULL"))
    empresa_id = Column(Integer, ForeignKey("mensura.empresas.id", ondelete="RESTRICT"), nullable=False)
    entregador_id = Column(Integer, ForeignKey("delivery.entregadores_dv.id", ondelete="SET NULL"))
    endereco_id = Column(Integer, ForeignKey("delivery.enderecos_dv.id", ondelete="SET NULL"), nullable=True)

    status = Column(String(1), nullable=False, default="P")  # Ex: P, E, F, C
    valor_total = Column(Numeric(18, 2), nullable=False)
    data_criacao = Column(DateTime, default=datetime.now)
    observacao_geral = Column(String(255), nullable=True)

    # Relacionamentos
    cliente = relationship("ClienteDeliveryModel", back_populates="pedidos")
    empresa = relationship("EmpresaModel", back_populates="pedidos")
    entregador = relationship("EntregadorDeliveryModel", back_populates="pedidos")
    endereco = relationship("EnderecoDeliveryModel", back_populates="pedidos")
    itens = relationship("PedidoItemModel", back_populates="pedido", cascade="all, delete-orphan")
    transacao = relationship("TransacaoPagamentoModel", back_populates="pedido", uselist=False,cascade="all, delete-orphan")


    model_config = ConfigDict(from_attributes=True)

