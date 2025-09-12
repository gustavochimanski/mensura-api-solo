from decimal import Decimal

from pydantic import ConfigDict
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Numeric, Enum as SAEnum, Date, func, JSON, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geography
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed

PedidoStatus = SAEnum(
    "P", "R", "S", "E", "C",
    name="pedido_status_enum",
    create_type=False
)

# PENDENTE: P
# EM_PREPARO: R
# SAIU_PARA_ENTREGA: S
# ENTREGUE: E
# CANCELADO: C

TipoEntrega = SAEnum("DELIVERY", "RETIRADA", name="tipo_entrega_enum", create_type=False)
OrigemPedido = SAEnum("WEB", "APP", "BALCAO", name="origem_pedido_enum", create_type=False)

#
class PedidoDeliveryModel(Base):
    __tablename__ = "pedidos_dv"
    __table_args__ = (
        Index("idx_pedidos_endereco_snapshot_gin", "endereco_snapshot", postgresql_using="gin"),
        # Index("idx_pedidos_endereco_geo_gist", "endereco_geo", postgresql_using="gist"),  # TEMPORARIAMENTE COMENTADO
        {"schema": "delivery"}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    empresa_id = Column(Integer, ForeignKey("mensura.empresas.id", ondelete="RESTRICT"), nullable=False)
    empresa = relationship("EmpresaModel", back_populates="pedidos")

    entregador_id = Column(Integer, ForeignKey("delivery.entregadores_dv.id", ondelete="SET NULL"))
    entregador = relationship("EntregadorDeliveryModel", back_populates="pedidos")

    endereco_id = Column(Integer, ForeignKey("delivery.enderecos_dv.id", ondelete="SET NULL"), nullable=True)
    endereco = relationship("EnderecoDeliveryModel", back_populates="pedidos")

    meio_pagamento_id = Column(Integer, ForeignKey("delivery.meios_pagamento_dv.id", ondelete="SET NULL"), nullable=True)
    meio_pagamento = relationship("MeioPagamentoModel")

    cliente_id = Column(Integer, ForeignKey("delivery.clientes_dv.id", ondelete="CASCADE"), nullable=False)
    cliente = relationship(
        "ClienteDeliveryModel",
        back_populates="pedidos",
        foreign_keys=[cliente_id]
    )

    status = Column(PedidoStatus, nullable=False, default="P")
    tipo_entrega = Column(TipoEntrega, nullable=False, default="DELIVERY")
    origem = Column(OrigemPedido, nullable=False, default="WEB")

    # totais
    subtotal = Column(Numeric(18, 2), nullable=False, default=0)
    desconto = Column(Numeric(18, 2), nullable=False, default=0)
    taxa_entrega = Column(Numeric(18, 2), nullable=False, default=0)
    taxa_servico = Column(Numeric(18, 2), nullable=False, default=0)
    valor_total = Column(Numeric(18, 2), nullable=False)

    previsao_entrega = Column(DateTime, nullable=True)
    distancia_km = Column(Numeric(10, 3), nullable=True)
    observacao_geral = Column(String(255), nullable=True)
    troco_para = Column(Numeric(18, 2), nullable=True)

    cupom_id = Column(Integer, ForeignKey("delivery.cupons_dv.id", ondelete="SET NULL"), nullable=True)
    cupom = relationship("CupomDescontoModel", back_populates="pedidos")

    # SNAPSHOT DO ENDEREÇO - dados congelados no momento da criação do pedido
    endereco_snapshot = Column(JSONB, nullable=False)  # Dados completos do endereço no momento do pedido
    # endereco_geo = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)  # Ponto geográfico para consultas avançadas - TEMPORARIAMENTE COMENTADO
    
    data_criacao = Column(DateTime, default=now_trimmed, nullable=False)
    data_atualizacao = Column(DateTime, default=now_trimmed, onupdate=now_trimmed,  nullable=False)

    itens = relationship("PedidoItemModel", back_populates="pedido", cascade="all, delete-orphan")
    transacao = relationship("TransacaoPagamentoModel", back_populates="pedido", uselist=False,
                             cascade="all, delete-orphan")
    historicos = relationship("PedidoStatusHistoricoModel", back_populates="pedido", cascade="all, delete-orphan")


    # ---- PROPRIEDADES CALCULADAS ----
    @property
    def subtotal_calc(self) -> Decimal:
        return sum(
            (item.preco_unitario or Decimal("0")) * (item.quantidade or 0)
            for item in self.itens
        ) or Decimal("0")

    @property
    def valor_total_calc(self) -> Decimal:
        subtotal = self.subtotal_calc
        desconto = self.desconto or Decimal("0")
        taxa_entrega = self.taxa_entrega or Decimal("0")
        taxa_servico = self.taxa_servico or Decimal("0")
        total = subtotal - desconto + taxa_entrega + taxa_servico
        return total if total > 0 else Decimal("0")

    model_config = ConfigDict(from_attributes=True)
