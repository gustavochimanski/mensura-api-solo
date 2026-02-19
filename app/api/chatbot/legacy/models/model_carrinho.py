# app/api/chatbot/models/model_carrinho.py
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Numeric, Enum as SAEnum,
    UniqueConstraint, Index, Boolean, JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import enum

from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class TipoEntregaCarrinho(enum.Enum):
    """Tipos de entrega/modalidade do carrinho temporário."""
    DELIVERY = "DELIVERY"
    RETIRADA = "RETIRADA"
    BALCAO = "BALCAO"
    MESA = "MESA"


# ENUM do PostgreSQL no schema chatbot
TipoEntregaCarrinhoEnum = SAEnum(
    "DELIVERY", "RETIRADA", "BALCAO", "MESA",
    name="tipo_entrega_carrinho_enum",
    create_type=False,
    schema="chatbot"
)


class CarrinhoTemporarioModel(Base):
    """
    Modelo de carrinho temporário no schema chatbot.
    
    Armazena pedidos em construção via chatbot antes de serem finalizados no checkout.
    Após confirmação no checkout, os dados são transferidos para pedidos.pedidos e este registro é excluído.
    """
    __tablename__ = "carrinho_temporario"
    __table_args__ = (
        Index("idx_carrinho_user_id", "user_id"),
        Index("idx_carrinho_empresa", "empresa_id"),
        Index("idx_carrinho_created_at", "created_at"),
        {"schema": "chatbot"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identificação do usuário (telefone WhatsApp)
    user_id = Column(String(50), nullable=False, index=True)  # Telefone do cliente
    
    # Empresa
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id", ondelete="RESTRICT"), nullable=False)
    empresa = relationship("EmpresaModel", lazy="select")
    
    # Tipo de entrega/modalidade
    tipo_entrega = Column(TipoEntregaCarrinhoEnum, nullable=False)
    
    # Relacionamentos específicos por tipo
    mesa_id = Column(Integer, ForeignKey("cadastros.mesas.id", ondelete="SET NULL"), nullable=True)
    mesa = relationship("MesaModel", lazy="select")
    
    cliente_id = Column(Integer, ForeignKey("cadastros.clientes.id", ondelete="SET NULL"), nullable=True)
    cliente = relationship("ClienteModel", lazy="select")
    
    # Campos específicos para Delivery
    endereco_id = Column(Integer, ForeignKey("cadastros.enderecos.id", ondelete="SET NULL"), nullable=True)
    endereco = relationship("EnderecoModel", lazy="select")
    
    meio_pagamento_id = Column(Integer, ForeignKey("cadastros.meios_pagamento.id", ondelete="SET NULL"), nullable=True)
    meio_pagamento = relationship("MeioPagamentoModel", lazy="select")
    
    cupom_id = Column(Integer, ForeignKey("cadastros.cupons_dv.id", ondelete="SET NULL"), nullable=True)
    cupom = relationship("CupomDescontoModel", lazy="select")
    
    # Observações
    observacoes = Column(String(500), nullable=True)
    observacao_geral = Column(String(255), nullable=True)
    num_pessoas = Column(Integer, nullable=True)  # Para mesa
    
    # Valores
    subtotal = Column(Numeric(18, 2), nullable=False, default=0)
    desconto = Column(Numeric(18, 2), nullable=False, default=0)
    taxa_entrega = Column(Numeric(18, 2), nullable=False, default=0)
    taxa_servico = Column(Numeric(18, 2), nullable=False, default=0)
    valor_total = Column(Numeric(18, 2), nullable=False, default=0)
    troco_para = Column(Numeric(18, 2), nullable=True)
    
    # Snapshots (dados congelados)
    endereco_snapshot = Column(JSONB, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=now_trimmed, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now_trimmed, onupdate=now_trimmed, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Para limpeza automática de carrinhos abandonados
    
    # Relacionamentos
    itens = relationship(
        "CarrinhoItemModel",
        back_populates="carrinho",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    def calcular_subtotal(self) -> Decimal:
        """Calcula o subtotal baseado nos itens do carrinho."""
        return sum(
            (item.preco_unitario or Decimal("0")) * (item.quantidade or 0)
            for item in self.itens
        ) or Decimal("0")
    
    def calcular_total(self) -> Decimal:
        """Calcula o valor total baseado no subtotal, descontos e taxas."""
        subtotal = self.calcular_subtotal()
        desconto = self.desconto or Decimal("0")
        taxa_entrega = self.taxa_entrega or Decimal("0")
        taxa_servico = self.taxa_servico or Decimal("0")
        total = subtotal - desconto + taxa_entrega + taxa_servico
        return total if total > 0 else Decimal("0")
