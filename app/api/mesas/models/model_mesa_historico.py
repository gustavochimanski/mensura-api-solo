# app/api/mesas/models/model_mesa_historico.py
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, func
from sqlalchemy.orm import relationship
import enum

from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class TipoOperacaoMesa(enum.Enum):
    """Tipos de operações que podem ser registradas no histórico"""
    STATUS_ALTERADO = "STATUS_ALTERADO"
    MESA_CRIADA = "MESA_CRIADA"
    MESA_ATUALIZADA = "MESA_ATUALIZADA"
    MESA_OCUPADA = "MESA_OCUPADA"
    MESA_LIBERADA = "MESA_LIBERADA"
    MESA_RESERVADA = "MESA_RESERVADA"
    CLIENTE_ASSOCIADO = "CLIENTE_ASSOCIADO"
    CLIENTE_DESASSOCIADO = "CLIENTE_DESASSOCIADO"
    PEDIDO_CRIADO = "PEDIDO_CRIADO"
    PEDIDO_FINALIZADO = "PEDIDO_FINALIZADO"
    MESA_DELETADA = "MESA_DELETADA"


class MesaHistoricoModel(Base):
    __tablename__ = "mesa_historico"
    __table_args__ = {"schema": "mesas"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Relacionamento com mesa
    mesa_id = Column(Integer, ForeignKey("mesas.mesa.id", ondelete="CASCADE"), nullable=False)
    mesa = relationship("MesaModel", back_populates="historico")
    
    # Relacionamento com cliente (opcional)
    cliente_id = Column(Integer, ForeignKey("delivery.clientes_dv.id", ondelete="SET NULL"), nullable=True)
    cliente = relationship("ClienteDeliveryModel")
    
    # Relacionamento com usuário que executou a operação (opcional)
    usuario_id = Column(Integer, ForeignKey("mensura.usuarios.id", ondelete="SET NULL"), nullable=True)
    usuario = relationship("UserModel")
    
    # Dados da operação
    tipo_operacao = Column(Enum(TipoOperacaoMesa), nullable=False)
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
        descricoes = {
            TipoOperacaoMesa.STATUS_ALTERADO: "Status alterado",
            TipoOperacaoMesa.MESA_CRIADA: "Mesa criada",
            TipoOperacaoMesa.MESA_ATUALIZADA: "Mesa atualizada",
            TipoOperacaoMesa.MESA_OCUPADA: "Mesa ocupada",
            TipoOperacaoMesa.MESA_LIBERADA: "Mesa liberada",
            TipoOperacaoMesa.MESA_RESERVADA: "Mesa reservada",
            TipoOperacaoMesa.CLIENTE_ASSOCIADO: "Cliente associado",
            TipoOperacaoMesa.CLIENTE_DESASSOCIADO: "Cliente desassociado",
            TipoOperacaoMesa.PEDIDO_CRIADO: "Pedido criado",
            TipoOperacaoMesa.PEDIDO_FINALIZADO: "Pedido finalizado",
            TipoOperacaoMesa.MESA_DELETADA: "Mesa deletada"
        }
        return descricoes.get(self.tipo_operacao, "Operação desconhecida")
    
    @property
    def resumo_operacao(self) -> str:
        """Retorna um resumo da operação"""
        if self.tipo_operacao == TipoOperacaoMesa.STATUS_ALTERADO:
            return f"Status alterado de '{self.status_anterior}' para '{self.status_novo}'"
        elif self.tipo_operacao == TipoOperacaoMesa.CLIENTE_ASSOCIADO:
            return f"Cliente associado à mesa"
        elif self.tipo_operacao == TipoOperacaoMesa.CLIENTE_DESASSOCIADO:
            return f"Cliente desassociado da mesa"
        elif self.tipo_operacao == TipoOperacaoMesa.PEDIDO_CRIADO:
            return f"Novo pedido criado"
        elif self.tipo_operacao == TipoOperacaoMesa.PEDIDO_FINALIZADO:
            return f"Pedido finalizado"
        else:
            return self.tipo_operacao_descricao
