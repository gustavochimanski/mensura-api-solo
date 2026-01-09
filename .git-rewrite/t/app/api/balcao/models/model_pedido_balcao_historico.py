# app/api/balcao/models/model_pedido_balcao_historico.py
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum, Index
from sqlalchemy.orm import relationship
import enum

from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class TipoOperacaoPedidoBalcao(enum.Enum):
    """Tipos de operações que podem ser registradas no histórico"""
    PEDIDO_CRIADO = "PEDIDO_CRIADO"
    STATUS_ALTERADO = "STATUS_ALTERADO"
    ITEM_ADICIONADO = "ITEM_ADICIONADO"
    ITEM_REMOVIDO = "ITEM_REMOVIDO"
    PEDIDO_CONFIRMADO = "PEDIDO_CONFIRMADO"
    PEDIDO_CANCELADO = "PEDIDO_CANCELADO"
    PEDIDO_FECHADO = "PEDIDO_FECHADO"
    PEDIDO_REABERTO = "PEDIDO_REABERTO"
    CLIENTE_ASSOCIADO = "CLIENTE_ASSOCIADO"
    CLIENTE_DESASSOCIADO = "CLIENTE_DESASSOCIADO"
    MESA_ASSOCIADA = "MESA_ASSOCIADA"
    MESA_DESASSOCIADA = "MESA_DESASSOCIADA"


# ENUM do PostgreSQL com schema correto
TipoOperacaoPedidoBalcaoEnum = SAEnum(
    "PEDIDO_CRIADO", "STATUS_ALTERADO", "ITEM_ADICIONADO", "ITEM_REMOVIDO",
    "PEDIDO_CONFIRMADO", "PEDIDO_CANCELADO", "PEDIDO_FECHADO", "PEDIDO_REABERTO",
    "CLIENTE_ASSOCIADO", "CLIENTE_DESASSOCIADO", "MESA_ASSOCIADA", "MESA_DESASSOCIADA",
    name="tipooperacaopedidobalcao",
    create_type=False,
    schema="balcao"
)


class PedidoBalcaoHistoricoModel(Base):
    __tablename__ = "pedido_balcao_historico"
    __table_args__ = (
        Index("idx_hist_pedido_balcao", "pedido_id"),
        Index("idx_hist_tipo_operacao_balcao", "tipo_operacao"),
        Index("idx_hist_created_at_balcao", "created_at"),
        Index("idx_hist_pedido_tipo_balcao", "pedido_id", "tipo_operacao"),
        Index("idx_hist_pedido_created_at_balcao", "pedido_id", "created_at"),
        {"schema": "balcao"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Relacionamento com pedido
    pedido_id = Column(Integer, ForeignKey("balcao.pedidos_balcao.id", ondelete="CASCADE"), nullable=False)
    pedido = relationship("PedidoBalcaoModel", back_populates="historico")
    
    # Relacionamento com cliente (opcional)
    cliente_id = Column(Integer, ForeignKey("cadastros.clientes.id", ondelete="SET NULL"), nullable=True)
    cliente = relationship("ClienteModel", lazy="select")
    
    # Relacionamento com usuário que executou a operação (opcional)
    usuario_id = Column(Integer, ForeignKey("cadastros.usuarios.id", ondelete="SET NULL"), nullable=True)
    usuario = relationship("UserModel", lazy="select")
    
    # Dados da operação
    tipo_operacao = Column(TipoOperacaoPedidoBalcaoEnum, nullable=False)
    status_anterior = Column(String(50), nullable=True)  # Status anterior (se aplicável)
    status_novo = Column(String(50), nullable=True)      # Status novo (se aplicável)
    descricao = Column(Text, nullable=True)          # Descrição da operação
    observacoes = Column(Text, nullable=True)        # Observações adicionais
    
    # Dados de contexto
    ip_origem = Column(String(45), nullable=True)     # IP de origem da operação
    user_agent = Column(String(500), nullable=True)   # User agent (se aplicável)
    
    # Timestamp
    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    
    @property
    def tipo_operacao_descricao(self) -> str:
        """Retorna a descrição do tipo de operação"""
        tipo_key = (
            self.tipo_operacao.value
            if isinstance(self.tipo_operacao, TipoOperacaoPedidoBalcao)
            else str(self.tipo_operacao)
        )
        descricoes = {
            TipoOperacaoPedidoBalcao.PEDIDO_CRIADO.value: "Pedido criado",
            TipoOperacaoPedidoBalcao.STATUS_ALTERADO.value: "Status alterado",
            TipoOperacaoPedidoBalcao.ITEM_ADICIONADO.value: "Item adicionado",
            TipoOperacaoPedidoBalcao.ITEM_REMOVIDO.value: "Item removido",
            TipoOperacaoPedidoBalcao.PEDIDO_CONFIRMADO.value: "Pedido confirmado",
            TipoOperacaoPedidoBalcao.PEDIDO_CANCELADO.value: "Pedido cancelado",
            TipoOperacaoPedidoBalcao.PEDIDO_FECHADO.value: "Pedido fechado",
            TipoOperacaoPedidoBalcao.PEDIDO_REABERTO.value: "Pedido reaberto",
            TipoOperacaoPedidoBalcao.CLIENTE_ASSOCIADO.value: "Cliente associado",
            TipoOperacaoPedidoBalcao.CLIENTE_DESASSOCIADO.value: "Cliente desassociado",
            TipoOperacaoPedidoBalcao.MESA_ASSOCIADA.value: "Mesa associada",
            TipoOperacaoPedidoBalcao.MESA_DESASSOCIADA.value: "Mesa desassociada",
        }
        return descricoes.get(tipo_key, "Operação desconhecida")
    
    @property
    def resumo_operacao(self) -> str:
        """Retorna um resumo da operação"""
        tipo_key = (
            self.tipo_operacao.value
            if isinstance(self.tipo_operacao, TipoOperacaoPedidoBalcao)
            else str(self.tipo_operacao)
        )
        if tipo_key == TipoOperacaoPedidoBalcao.STATUS_ALTERADO.value:
            return f"Status alterado de '{self.status_anterior}' para '{self.status_novo}'"
        elif tipo_key == TipoOperacaoPedidoBalcao.CLIENTE_ASSOCIADO.value:
            return f"Cliente associado ao pedido"
        elif tipo_key == TipoOperacaoPedidoBalcao.CLIENTE_DESASSOCIADO.value:
            return f"Cliente desassociado do pedido"
        elif tipo_key == TipoOperacaoPedidoBalcao.MESA_ASSOCIADA.value:
            return f"Mesa associada ao pedido"
        elif tipo_key == TipoOperacaoPedidoBalcao.MESA_DESASSOCIADA.value:
            return f"Mesa desassociada do pedido"
        elif tipo_key == TipoOperacaoPedidoBalcao.ITEM_ADICIONADO.value:
            return f"Item adicionado ao pedido"
        elif tipo_key == TipoOperacaoPedidoBalcao.ITEM_REMOVIDO.value:
            return f"Item removido do pedido"
        else:
            return self.tipo_operacao_descricao

