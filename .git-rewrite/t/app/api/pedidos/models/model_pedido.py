# app/api/pedidos/models/model_pedido.py
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Enum as SAEnum, UniqueConstraint, Index, JSON, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography
import enum

from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class TipoPedido(enum.Enum):
    """Tipos de pedidos suportados."""
    MESA = "MESA"
    BALCAO = "BALCAO"
    DELIVERY = "DELIVERY"


class StatusPedido(enum.Enum):
    """Status possíveis para um pedido.
    
    Status compartilhados entre todos os tipos de pedidos:
    - P: Pendente
    - I: Impressão
    - R: Preparando
    - S: Saiu para entrega (apenas delivery)
    - E: Entregue/Concluído
    - C: Cancelado
    - D: Editado
    - X: Em edição
    - A: Aguardando pagamento
    """
    PENDENTE = "P"
    IMPRESSAO = "I"
    PREPARANDO = "R"
    SAIU_PARA_ENTREGA = "S"
    ENTREGUE = "E"
    CANCELADO = "C"
    EDITADO = "D"
    EM_EDICAO = "X"
    AGUARDANDO_PAGAMENTO = "A"


# ENUMs do PostgreSQL
TipoPedidoEnum = SAEnum(
    "MESA", "BALCAO", "DELIVERY",
    name="tipo_pedido_enum",
    create_type=False,
    schema="pedidos"
)

StatusPedidoEnum = SAEnum(
    "P", "I", "R", "S", "E", "C", "D", "X", "A",
    name="status_pedido_enum",
    create_type=False,
    schema="pedidos"
)

TipoEntregaEnum = SAEnum(
    "DELIVERY", "RETIRADA",
    name="tipo_entrega_enum",
    create_type=False,
    schema="pedidos"
)

OrigemPedidoEnum = SAEnum(
    "WEB", "APP", "BALCAO",
    name="origem_pedido_enum",
    create_type=False,
    schema="pedidos"
)


class PedidoModel(Base):
    """
    Modelo unificado de pedidos.
    
    Centraliza todos os tipos de pedidos:
    - Pedidos de Mesa (mesa_id obrigatório)
    - Pedidos de Balcão (mesa_id opcional)
    - Pedidos de Delivery (endereco_id obrigatório, entregador_id opcional)
    """
    __tablename__ = "pedidos"
    __table_args__ = (
        UniqueConstraint("empresa_id", "numero_pedido", name="uq_pedidos_empresa_numero"),
        Index("idx_pedidos_empresa", "empresa_id"),
        Index("idx_pedidos_tipo_status", "tipo_pedido", "status"),
        Index("idx_pedidos_endereco_snapshot_gin", "endereco_snapshot", postgresql_using="gin"),
        Index("idx_pedidos_endereco_geo_gist", "endereco_geo", postgresql_using="gist"),
        {"schema": "pedidos"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Tipo de pedido (obrigatório)
    tipo_pedido = Column(TipoPedidoEnum, nullable=False)
    
    # Empresa (obrigatório)
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id", ondelete="RESTRICT"), nullable=False)
    empresa = relationship("EmpresaModel", lazy="select")
    
    # Relacionamentos específicos por tipo
    mesa_id = Column(Integer, ForeignKey("cadastros.mesas.id", ondelete="SET NULL"), nullable=True)
    mesa = relationship("MesaModel", lazy="select")
    
    cliente_id = Column(Integer, ForeignKey("cadastros.clientes.id", ondelete="SET NULL"), nullable=True)
    cliente = relationship("ClienteModel", lazy="select")
    
    # Campos específicos para Delivery
    entregador_id = Column(Integer, ForeignKey("cadastros.entregadores_dv.id", ondelete="SET NULL"), nullable=True)
    entregador = relationship("EntregadorDeliveryModel", lazy="select")
    
    endereco_id = Column(Integer, ForeignKey("cadastros.enderecos.id", ondelete="SET NULL"), nullable=True)
    endereco = relationship("EnderecoModel", lazy="select")
    
    meio_pagamento_id = Column(Integer, ForeignKey("cadastros.meios_pagamento.id", ondelete="SET NULL"), nullable=True)
    meio_pagamento = relationship("MeioPagamentoModel", lazy="select")
    
    cupom_id = Column(Integer, ForeignKey("cadastros.cupons_dv.id", ondelete="SET NULL"), nullable=True)
    cupom = relationship("CupomDescontoModel", lazy="select")
    
    # Dados do pedido
    numero_pedido = Column(String(20), nullable=False)
    status = Column(StatusPedidoEnum, nullable=False, default="P")
    
    # Campos específicos para Delivery
    tipo_entrega = Column(TipoEntregaEnum, nullable=True)  # Apenas para DELIVERY
    origem = Column(OrigemPedidoEnum, nullable=True)  # Apenas para DELIVERY
    
    # Observações e informações adicionais
    observacoes = Column(String(500), nullable=True)
    observacao_geral = Column(String(255), nullable=True)  # Para delivery
    num_pessoas = Column(Integer, nullable=True)  # Para mesa
    troco_para = Column(Numeric(18, 2), nullable=True)  # Para delivery
    
    # Valores
    subtotal = Column(Numeric(18, 2), nullable=False, default=0)
    desconto = Column(Numeric(18, 2), nullable=False, default=0)
    taxa_entrega = Column(Numeric(18, 2), nullable=False, default=0)  # Apenas para delivery
    taxa_servico = Column(Numeric(18, 2), nullable=False, default=0)
    valor_total = Column(Numeric(18, 2), nullable=False, default=0)
    
    # Campos específicos para Delivery
    previsao_entrega = Column(DateTime(timezone=True), nullable=True)
    distancia_km = Column(Numeric(10, 3), nullable=True)
    
    # Snapshot do endereço (para delivery)
    endereco_snapshot = Column(JSONB, nullable=True)
    endereco_geo = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    
    # Acerto com entregadores
    acertado_entregador = Column(Boolean, nullable=False, default=False)
    acertado_entregador_em = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=now_trimmed, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now_trimmed, onupdate=now_trimmed, nullable=False)
    
    # Relacionamentos
    itens = relationship("PedidoUnificadoItemModel", back_populates="pedido", cascade="all, delete-orphan")
    historico = relationship("PedidoHistoricoModel", back_populates="pedido", cascade="all, delete-orphan")
    
    # TODO: Transações de pagamento (para delivery) - será implementado quando necessário
    # transacao = relationship(
    #     "TransacaoPagamentoModel",
    #     foreign_keys="TransacaoPagamentoModel.pedido_id",
    #     back_populates="pedido",
    #     uselist=False,
    #     cascade="all, delete-orphan",
    #     overlaps="transacoes"
    # )
    # transacoes = relationship(
    #     "TransacaoPagamentoModel",
    #     foreign_keys="TransacaoPagamentoModel.pedido_id",
    #     back_populates="pedido_multi",
    #     cascade="all, delete-orphan",
    #     overlaps="transacao"
    # )

    @property
    def status_descricao(self) -> str:
        """Retorna a descrição do status"""
        status_key = (
            self.status.value
            if isinstance(self.status, StatusPedido)
            else str(self.status)
        )
        status_map = {
            StatusPedido.PENDENTE.value: "Pendente",
            StatusPedido.IMPRESSAO.value: "Em impressão",
            StatusPedido.PREPARANDO.value: "Preparando",
            StatusPedido.SAIU_PARA_ENTREGA.value: "Saiu para entrega",
            StatusPedido.ENTREGUE.value: "Entregue/Concluído",
            StatusPedido.CANCELADO.value: "Cancelado",
            StatusPedido.EDITADO.value: "Editado",
            StatusPedido.EM_EDICAO.value: "Em edição",
            StatusPedido.AGUARDANDO_PAGAMENTO.value: "Aguardando pagamento",
        }
        return status_map.get(status_key, "Desconhecido")

    @property
    def status_cor(self) -> str:
        """Retorna a cor do status para interface"""
        status_key = (
            self.status.value
            if isinstance(self.status, StatusPedido)
            else str(self.status)
        )
        cor_map = {
            StatusPedido.PENDENTE.value: "orange",
            StatusPedido.IMPRESSAO.value: "blue",
            StatusPedido.PREPARANDO.value: "yellow",
            StatusPedido.SAIU_PARA_ENTREGA.value: "cyan",
            StatusPedido.ENTREGUE.value: "green",
            StatusPedido.CANCELADO.value: "red",
            StatusPedido.EDITADO.value: "purple",
            StatusPedido.EM_EDICAO.value: "teal",
            StatusPedido.AGUARDANDO_PAGAMENTO.value: "cyan",
        }
        return cor_map.get(status_key, "gray")
    
    def is_delivery(self) -> bool:
        """Verifica se é um pedido de delivery"""
        return self.tipo_pedido == TipoPedido.DELIVERY.value if isinstance(self.tipo_pedido, str) else self.tipo_pedido == TipoPedido.DELIVERY
    
    def is_mesa(self) -> bool:
        """Verifica se é um pedido de mesa"""
        return self.tipo_pedido == TipoPedido.MESA.value if isinstance(self.tipo_pedido, str) else self.tipo_pedido == TipoPedido.MESA
    
    def is_balcao(self) -> bool:
        """Verifica se é um pedido de balcão"""
        return self.tipo_pedido == TipoPedido.BALCAO.value if isinstance(self.tipo_pedido, str) else self.tipo_pedido == TipoPedido.BALCAO

