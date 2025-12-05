# app/api/cardapio/models/model_pedido_unificado.py
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Numeric, Enum as SAEnum,
    UniqueConstraint, Index, Boolean, JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geography
from sqlalchemy.orm import relationship
import enum

from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class StatusPedido(enum.Enum):
    """Status possíveis para um pedido.
    
    Status compartilhados entre todos os tipos de pedidos:
    - P: Pendente
    - I: Pendente Impressão / Em Impressão
    - R: Em Preparo / Preparando
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


class TipoEntrega(enum.Enum):
    """Tipos de entrega/modalidade do pedido."""
    DELIVERY = "DELIVERY"
    RETIRADA = "RETIRADA"
    BALCAO = "BALCAO"
    MESA = "MESA"


class CanalPedido(enum.Enum):
    """Canal de origem do pedido (apenas para delivery)."""
    WEB = "WEB"
    APP = "APP"
    BALCAO = "BALCAO"


# ENUMs do PostgreSQL no schema pedidos
StatusPedidoEnum = SAEnum(
    "P", "I", "R", "S", "E", "C", "D", "X", "A",
    name="pedido_status_enum",
    create_type=False,
    schema="pedidos"
)

TipoEntregaEnum = SAEnum(
    "DELIVERY", "RETIRADA", "BALCAO", "MESA",
    name="tipo_entrega_enum",
    create_type=False,
    schema="pedidos"
)

CanalPedidoEnum = SAEnum(
    "WEB", "APP", "BALCAO",
    name="canal_pedido_enum",
    create_type=False,
    schema="pedidos"
)


class PedidoUnificadoModel(Base):
    """
    Modelo unificado de pedidos no schema pedidos.
    
    Centraliza todos os tipos de pedidos:
    - tipo_entrega: DELIVERY, RETIRADA, BALCAO ou MESA (modalidade do pedido)
    """
    __tablename__ = "pedidos"
    __table_args__ = (
        UniqueConstraint("empresa_id", "numero_pedido", name="uq_pedidos_empresa_numero"),
        Index("idx_pedidos_empresa", "empresa_id"),
        Index("idx_pedidos_empresa_tipo_status", "empresa_id", "tipo_entrega", "status"),
        Index("idx_pedidos_tipo_status", "tipo_entrega", "status"),
        Index("idx_pedidos_numero", "empresa_id", "numero_pedido"),
        Index("idx_pedidos_endereco_snapshot_gin", "endereco_snapshot", postgresql_using="gin"),
        Index("idx_pedidos_endereco_geo_gist", "endereco_geo", postgresql_using="gist"),
        {"schema": "pedidos"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Tipo de entrega/modalidade (DELIVERY, RETIRADA, BALCAO, MESA)
    tipo_entrega = Column(TipoEntregaEnum, nullable=False)
    
    # Empresa (obrigatório)
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id", ondelete="RESTRICT"), nullable=False)
    empresa = relationship("EmpresaModel", lazy="select")
    
    # Número do pedido (único por empresa)
    numero_pedido = Column(String(20), nullable=False)
    
    # Status do pedido
    status = Column(StatusPedidoEnum, nullable=False, default="P")
    
    # Relacionamentos específicos por tipo
    mesa_id = Column(Integer, ForeignKey("cadastros.mesas.id", ondelete="SET NULL"), nullable=True)
    mesa = relationship("MesaModel", lazy="select")
    
    cliente_id = Column(Integer, ForeignKey("cadastros.clientes.id", ondelete="SET NULL"), nullable=True)
    cliente = relationship("ClienteModel", lazy="select")
    
    # Campos específicos para Delivery
    endereco_id = Column(Integer, ForeignKey("cadastros.enderecos.id", ondelete="SET NULL"), nullable=True)
    endereco = relationship("EnderecoModel", lazy="select")
    
    entregador_id = Column(Integer, ForeignKey("cadastros.entregadores_dv.id", ondelete="SET NULL"), nullable=True)
    entregador = relationship("EntregadorDeliveryModel", lazy="select")
    
    meio_pagamento_id = Column(Integer, ForeignKey("cadastros.meios_pagamento.id", ondelete="SET NULL"), nullable=True)
    meio_pagamento = relationship("MeioPagamentoModel", lazy="select")
    
    cupom_id = Column(Integer, ForeignKey("cadastros.cupons_dv.id", ondelete="SET NULL"), nullable=True)
    cupom = relationship("CupomDescontoModel", lazy="select")
    
    # Canal de origem (apenas para delivery)
    canal = Column(CanalPedidoEnum, nullable=True)  # WEB, APP, BALCAO
    
    # Observações e informações adicionais
    observacoes = Column(String(500), nullable=True)  # Para balcão e mesa
    observacao_geral = Column(String(255), nullable=True)  # Para delivery
    num_pessoas = Column(Integer, nullable=True)  # Para mesa
    
    # Valores
    subtotal = Column(Numeric(18, 2), nullable=False, default=0)
    desconto = Column(Numeric(18, 2), nullable=False, default=0)
    taxa_entrega = Column(Numeric(18, 2), nullable=False, default=0)  # Apenas para delivery
    taxa_servico = Column(Numeric(18, 2), nullable=False, default=0)
    valor_total = Column(Numeric(18, 2), nullable=False, default=0)
    troco_para = Column(Numeric(18, 2), nullable=True)
    
    # Campos específicos para Delivery
    previsao_entrega = Column(DateTime(timezone=True), nullable=True)
    distancia_km = Column(Numeric(10, 3), nullable=True)
    
    # Snapshots (dados congelados no momento da criação do pedido)
    endereco_snapshot = Column(JSONB, nullable=True)  # Para delivery
    endereco_geo = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)  # Para delivery
    
    # Acerto com entregadores (apenas para delivery)
    acertado_entregador = Column(Boolean, nullable=False, default=False)
    acertado_entregador_em = Column(DateTime(timezone=True), nullable=True)
    
    # Status de pagamento
    pago = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=now_trimmed, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now_trimmed, onupdate=now_trimmed, nullable=False)
    
    # Relacionamentos
    itens = relationship("PedidoItemUnificadoModel", back_populates="pedido", cascade="all, delete-orphan")
    historico = relationship("PedidoHistoricoUnificadoModel", back_populates="pedido", cascade="all, delete-orphan")
    
    # Relacionamento com transações de pagamento (para delivery)
    transacao = relationship(
        "TransacaoPagamentoModel",
        foreign_keys="TransacaoPagamentoModel.pedido_id",
        back_populates="pedido",
        uselist=False,
        cascade="all, delete-orphan",
        overlaps="pedido_multi,transacoes"
    )
    transacoes = relationship(
        "TransacaoPagamentoModel",
        foreign_keys="TransacaoPagamentoModel.pedido_id",
        cascade="all, delete-orphan",
        overlaps="pedido,transacao"
    )
    
    # ---- PROPRIEDADES CALCULADAS ----
    @property
    def subtotal_calc(self) -> Decimal:
        """Calcula o subtotal baseado nos itens do pedido."""
        return sum(
            (item.preco_unitario or Decimal("0")) * (item.quantidade or 0)
            for item in self.itens
        ) or Decimal("0")

    @property
    def valor_total_calc(self) -> Decimal:
        """Calcula o valor total baseado no subtotal, descontos e taxas."""
        subtotal = self.subtotal_calc
        desconto = self.desconto or Decimal("0")
        taxa_entrega = self.taxa_entrega or Decimal("0")
        taxa_servico = self.taxa_servico or Decimal("0")
        total = subtotal - desconto + taxa_entrega + taxa_servico
        return total if total > 0 else Decimal("0")
    
    @property
    def status_descricao(self) -> str:
        """Retorna a descrição do status."""
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
        """Retorna a cor do status para interface."""
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
        """Verifica se é um pedido de delivery."""
        return (
            self.tipo_entrega == TipoEntrega.DELIVERY.value
            if isinstance(self.tipo_entrega, str)
            else self.tipo_entrega == TipoEntrega.DELIVERY
        )
    
    def is_mesa(self) -> bool:
        """Verifica se é um pedido de mesa."""
        return (
            self.tipo_entrega == TipoEntrega.MESA.value
            if isinstance(self.tipo_entrega, str)
            else self.tipo_entrega == TipoEntrega.MESA
        )
    
    def is_balcao(self) -> bool:
        """Verifica se é um pedido de balcão."""
        return (
            self.tipo_entrega == TipoEntrega.BALCAO.value
            if isinstance(self.tipo_entrega, str)
            else self.tipo_entrega == TipoEntrega.BALCAO
        )
    
    def is_retirada(self) -> bool:
        """Verifica se é um pedido para retirada."""
        return (
            self.tipo_entrega == TipoEntrega.RETIRADA.value
            if isinstance(self.tipo_entrega, str)
            else self.tipo_entrega == TipoEntrega.RETIRADA
        )

