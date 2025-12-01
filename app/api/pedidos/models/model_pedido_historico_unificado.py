# app/api/cardapio/models/model_pedido_historico_unificado.py
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum, Index
)
from sqlalchemy.orm import relationship
import enum

from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed
from .model_pedido_unificado import StatusPedidoEnum, TipoPedidoEnum


class TipoOperacaoPedido(enum.Enum):
    """
    Tipos de operações que podem ser registradas no histórico.
    
    Suporta histórico detalhado (como balcão) e histórico simples (apenas status).
    """
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
    ENTREGADOR_ASSOCIADO = "ENTREGADOR_ASSOCIADO"
    ENTREGADOR_DESASSOCIADO = "ENTREGADOR_DESASSOCIADO"
    ENDERECO_ALTERADO = "ENDERECO_ALTERADO"
    PAGAMENTO_REALIZADO = "PAGAMENTO_REALIZADO"
    PAGAMENTO_CANCELADO = "PAGAMENTO_CANCELADO"


# ENUM do PostgreSQL no schema cardapio
TipoOperacaoPedidoEnum = SAEnum(
    "PEDIDO_CRIADO", "STATUS_ALTERADO", "ITEM_ADICIONADO", "ITEM_REMOVIDO",
    "PEDIDO_CONFIRMADO", "PEDIDO_CANCELADO", "PEDIDO_FECHADO", "PEDIDO_REABERTO",
    "CLIENTE_ASSOCIADO", "CLIENTE_DESASSOCIADO", "MESA_ASSOCIADA", "MESA_DESASSOCIADA",
    "ENTREGADOR_ASSOCIADO", "ENTREGADOR_DESASSOCIADO", "ENDERECO_ALTERADO",
    "PAGAMENTO_REALIZADO", "PAGAMENTO_CANCELADO",
    name="tipo_operacao_pedido_enum",
    create_type=False,
    schema="pedidos"
)


class PedidoHistoricoUnificadoModel(Base):
    """
    Modelo unificado de histórico de pedidos no schema pedidos.
    
    Suporta dois tipos de histórico:
    1. Histórico simples (apenas mudança de status):
       - status_anterior e status_novo preenchidos
       - tipo_pedido: DELIVERY, MESA ou BALCAO (tipo do pedido)
       - tipo_operacao pode ser NULL ou STATUS_ALTERADO
       - Usado principalmente para delivery
    
    2. Histórico detalhado (com tipo_operacao):
       - tipo_pedido: DELIVERY, MESA ou BALCAO (tipo do pedido)
       - tipo_operacao preenchido (PEDIDO_CRIADO, ITEM_ADICIONADO, etc.)
       - status_anterior e status_novo podem ser NULL (dependendo da operação)
       - Usado principalmente para balcão e mesa
    """
    __tablename__ = "pedidos_historico"
    __table_args__ = (
        Index("idx_pedidos_historico_pedido", "pedido_id"),
        Index("idx_pedidos_historico_tipo_pedido", "tipo_pedido"),
        Index("idx_pedidos_historico_tipo_operacao", "tipo_operacao"),
        Index("idx_pedidos_historico_status_novo", "status_novo"),
        Index("idx_pedidos_historico_created_at", "created_at"),
        Index("idx_pedidos_historico_pedido_tipo", "pedido_id", "tipo_pedido"),
        Index("idx_pedidos_historico_pedido_created_at", "pedido_id", "created_at"),
        {"schema": "pedidos"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Relacionamento com pedido
    pedido_id = Column(
        Integer,
        ForeignKey("pedidos.pedidos.id", ondelete="CASCADE"),
        nullable=False
    )
    pedido = relationship("PedidoUnificadoModel", back_populates="historico")
    
    # Tipo do pedido (DELIVERY, MESA, BALCAO)
    tipo_pedido = Column(TipoPedidoEnum, nullable=True)
    
    # Tipo de operação (nullable - para histórico detalhado)
    tipo_operacao = Column(TipoOperacaoPedidoEnum, nullable=True)
    
    # Status anterior e novo (nullable - para histórico de mudança de status)
    status_anterior = Column(StatusPedidoEnum, nullable=True)
    status_novo = Column(StatusPedidoEnum, nullable=True)
    
    # Descrição da operação
    descricao = Column(Text, nullable=True)
    
    # Motivo da mudança (usado principalmente em delivery)
    motivo = Column(Text, nullable=True)
    
    # Observações adicionais
    observacoes = Column(Text, nullable=True)
    
    # Relacionamentos
    usuario_id = Column(
        Integer,
        ForeignKey("cadastros.usuarios.id", ondelete="SET NULL"),
        nullable=True
    )
    usuario = relationship("UserModel", lazy="select")
    
    cliente_id = Column(
        Integer,
        ForeignKey("cadastros.clientes.id", ondelete="SET NULL"),
        nullable=True
    )
    cliente = relationship("ClienteModel", lazy="select")
    
    # Dados de contexto
    ip_origem = Column(String(45), nullable=True)  # IP de origem da operação (IPv4/IPv6)
    user_agent = Column(String(500), nullable=True)  # User agent do cliente
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), default=now_trimmed, nullable=False)
    
    @property
    def tipo_operacao_descricao(self) -> str:
        """Retorna a descrição do tipo de operação."""
        if self.tipo_operacao is None:
            return "Operação sem tipo"
        
        tipo_key = (
            self.tipo_operacao.value
            if isinstance(self.tipo_operacao, TipoOperacaoPedido)
            else str(self.tipo_operacao)
        )
        descricoes = {
            TipoOperacaoPedido.PEDIDO_CRIADO.value: "Pedido criado",
            TipoOperacaoPedido.STATUS_ALTERADO.value: "Status alterado",
            TipoOperacaoPedido.ITEM_ADICIONADO.value: "Item adicionado",
            TipoOperacaoPedido.ITEM_REMOVIDO.value: "Item removido",
            TipoOperacaoPedido.PEDIDO_CONFIRMADO.value: "Pedido confirmado",
            TipoOperacaoPedido.PEDIDO_CANCELADO.value: "Pedido cancelado",
            TipoOperacaoPedido.PEDIDO_FECHADO.value: "Pedido fechado",
            TipoOperacaoPedido.PEDIDO_REABERTO.value: "Pedido reaberto",
            TipoOperacaoPedido.CLIENTE_ASSOCIADO.value: "Cliente associado",
            TipoOperacaoPedido.CLIENTE_DESASSOCIADO.value: "Cliente desassociado",
            TipoOperacaoPedido.MESA_ASSOCIADA.value: "Mesa associada",
            TipoOperacaoPedido.MESA_DESASSOCIADA.value: "Mesa desassociada",
            TipoOperacaoPedido.ENTREGADOR_ASSOCIADO.value: "Entregador associado",
            TipoOperacaoPedido.ENTREGADOR_DESASSOCIADO.value: "Entregador desassociado",
            TipoOperacaoPedido.ENDERECO_ALTERADO.value: "Endereço alterado",
            TipoOperacaoPedido.PAGAMENTO_REALIZADO.value: "Pagamento realizado",
            TipoOperacaoPedido.PAGAMENTO_CANCELADO.value: "Pagamento cancelado",
        }
        return descricoes.get(tipo_key, "Operação desconhecida")
    
    @property
    def resumo_operacao(self) -> str:
        """Retorna um resumo da operação."""
        # Se tem tipo_operacao, usa a descrição
        if self.tipo_operacao:
            tipo_key = (
                self.tipo_operacao.value
                if isinstance(self.tipo_operacao, TipoOperacaoPedido)
                else str(self.tipo_operacao)
            )
            
            if tipo_key == TipoOperacaoPedido.STATUS_ALTERADO.value:
                return f"Status alterado de '{self.status_anterior}' para '{self.status_novo}'"
            elif tipo_key == TipoOperacaoPedido.CLIENTE_ASSOCIADO.value:
                return "Cliente associado ao pedido"
            elif tipo_key == TipoOperacaoPedido.CLIENTE_DESASSOCIADO.value:
                return "Cliente desassociado do pedido"
            elif tipo_key == TipoOperacaoPedido.MESA_ASSOCIADA.value:
                return "Mesa associada ao pedido"
            elif tipo_key == TipoOperacaoPedido.MESA_DESASSOCIADA.value:
                return "Mesa desassociada do pedido"
            elif tipo_key == TipoOperacaoPedido.ENTREGADOR_ASSOCIADO.value:
                return "Entregador associado ao pedido"
            elif tipo_key == TipoOperacaoPedido.ENTREGADOR_DESASSOCIADO.value:
                return "Entregador desassociado do pedido"
            elif tipo_key == TipoOperacaoPedido.ITEM_ADICIONADO.value:
                return "Item adicionado ao pedido"
            elif tipo_key == TipoOperacaoPedido.ITEM_REMOVIDO.value:
                return "Item removido do pedido"
            else:
                return self.tipo_operacao_descricao
        
        # Se não tem tipo_operacao mas tem mudança de status, é histórico simples
        elif self.status_anterior is not None or self.status_novo is not None:
            return f"Status alterado de '{self.status_anterior}' para '{self.status_novo}'"
        
        # Fallback
        return self.descricao or "Operação registrada"
    
    def is_historico_detalhado(self) -> bool:
        """Verifica se é um histórico detalhado (com tipo_operacao)."""
        return self.tipo_operacao is not None
    
    def is_historico_status(self) -> bool:
        """Verifica se é um histórico de mudança de status."""
        return self.status_anterior is not None or self.status_novo is not None

