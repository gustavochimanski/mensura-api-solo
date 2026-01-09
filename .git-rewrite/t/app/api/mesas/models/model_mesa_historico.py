# app/api/mesas/models/model_mesa_historico.py
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum, func, Index
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


# ENUM do PostgreSQL com schema correto
TipoOperacaoMesaEnum = SAEnum(
    "STATUS_ALTERADO", "MESA_CRIADA", "MESA_ATUALIZADA", "MESA_OCUPADA", "MESA_LIBERADA",
    "MESA_RESERVADA", "CLIENTE_ASSOCIADO", "CLIENTE_DESASSOCIADO", "PEDIDO_CRIADO",
    "PEDIDO_FINALIZADO", "MESA_DELETADA",
    name="tipooperacaomesa",
    create_type=False,
    schema="mesas"
)


class MesaHistoricoModel(Base):
    __tablename__ = "mesa_historico"
    __table_args__ = (
        Index("idx_hist_mesa", "mesa_id"),
        Index("idx_hist_tipo_operacao", "tipo_operacao"),
        Index("idx_hist_created_at", "created_at"),
        Index("idx_hist_mesa_tipo", "mesa_id", "tipo_operacao"),
        Index("idx_hist_mesa_created_at", "mesa_id", "created_at"),
        {"schema": "mesas"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Relacionamento com mesa
    mesa_id = Column(Integer, ForeignKey("cadastros.mesas.id", ondelete="CASCADE"), nullable=False)
    mesa = relationship("MesaModel", back_populates="historico")
    
    # Relacionamento com cliente (opcional)
    cliente_id = Column(Integer, ForeignKey("cadastros.clientes.id", ondelete="SET NULL"), nullable=True)
    cliente = relationship("ClienteModel", lazy="select")
    
    # Relacionamento com usuário que executou a operação (opcional)
    usuario_id = Column(Integer, ForeignKey("cadastros.usuarios.id", ondelete="SET NULL"), nullable=True)
    usuario = relationship("UserModel", lazy="select")
    
    # Dados da operação
    tipo_operacao = Column(TipoOperacaoMesaEnum, nullable=False)
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
        # Converte para string se for enum
        tipo_str = self.tipo_operacao.value if isinstance(self.tipo_operacao, TipoOperacaoMesa) else str(self.tipo_operacao)
        
        descricoes = {
            "STATUS_ALTERADO": "Status alterado",
            "MESA_CRIADA": "Mesa criada",
            "MESA_ATUALIZADA": "Mesa atualizada",
            "MESA_OCUPADA": "Mesa ocupada",
            "MESA_LIBERADA": "Mesa liberada",
            "MESA_RESERVADA": "Mesa reservada",
            "CLIENTE_ASSOCIADO": "Cliente associado",
            "CLIENTE_DESASSOCIADO": "Cliente desassociado",
            "PEDIDO_CRIADO": "Pedido criado",
            "PEDIDO_FINALIZADO": "Pedido finalizado",
            "MESA_DELETADA": "Mesa deletada"
        }
        return descricoes.get(tipo_str, "Operação desconhecida")
    
    @property
    def resumo_operacao(self) -> str:
        """Retorna um resumo da operação"""
        # Converte para string se for enum
        tipo_str = self.tipo_operacao.value if isinstance(self.tipo_operacao, TipoOperacaoMesa) else str(self.tipo_operacao)
        
        if tipo_str == "STATUS_ALTERADO":
            return f"Status alterado de '{self.status_anterior}' para '{self.status_novo}'"
        elif tipo_str == "CLIENTE_ASSOCIADO":
            return f"Cliente associado à mesa"
        elif tipo_str == "CLIENTE_DESASSOCIADO":
            return f"Cliente desassociado da mesa"
        elif tipo_str == "PEDIDO_CRIADO":
            return f"Novo pedido criado"
        elif tipo_str == "PEDIDO_FINALIZADO":
            return f"Pedido finalizado"
        else:
            return self.tipo_operacao_descricao
