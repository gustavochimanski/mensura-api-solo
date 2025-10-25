# app/api/mesas/models/model_mesa.py
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, func, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
import enum

from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class StatusMesa(enum.Enum):
    """Status possíveis para uma mesa"""
    DISPONIVEL = "D"  # Disponível
    OCUPADA = "O"     # Ocupada
    LIVRE = "L"       # Livre
    RESERVADA = "R"   # Reservada


class MesaModel(Base):
    __tablename__ = "mesa"
    __table_args__ = {"schema": "mesas"}

    id = Column(Integer, primary_key=True)
    numero = Column(String(10), nullable=False, unique=True)
    descricao = Column(String(100), nullable=True)
    capacidade = Column(Integer, nullable=False, default=4)
    status = Column(Enum(StatusMesa), nullable=False, default=StatusMesa.DISPONIVEL)
    ativa = Column(String(1), nullable=False, default="S")  # S/N para ativa/inativa
    
    # Relacionamentos
    pedidos = relationship("PedidoMesaModel", back_populates="mesa", cascade="all, delete-orphan")
    cliente_atual_id = Column(Integer, ForeignKey("delivery.clientes_dv.id", ondelete="SET NULL"), nullable=True)
    cliente_atual = relationship("ClienteDeliveryModel", lazy="select")
    historico = relationship("MesaHistoricoModel", back_populates="mesa", cascade="all, delete-orphan")
    
    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)

    @hybrid_property
    def status_descricao(self) -> str:
        """Retorna a descrição do status"""
        status_map = {
            StatusMesa.DISPONIVEL: "Disponível",
            StatusMesa.OCUPADA: "Ocupada", 
            StatusMesa.LIVRE: "Livre",
            StatusMesa.RESERVADA: "Reservada"
        }
        return status_map.get(self.status, "Desconhecido")

    @hybrid_property
    def status_cor(self) -> str:
        """Retorna a cor do status para interface"""
        cor_map = {
            StatusMesa.DISPONIVEL: "green",
            StatusMesa.OCUPADA: "red",
            StatusMesa.LIVRE: "blue", 
            StatusMesa.RESERVADA: "orange"
        }
        return cor_map.get(self.status, "gray")

    @property
    def label(self) -> str:
        """Label para exibição"""
        return f"Mesa {self.numero}"

    @property
    def is_ocupada(self) -> bool:
        """Verifica se a mesa está ocupada"""
        return self.status == StatusMesa.OCUPADA

    @property
    def is_disponivel(self) -> bool:
        """Verifica se a mesa está disponível"""
        return self.status == StatusMesa.DISPONIVEL

    @property
    def is_reservada(self) -> bool:
        """Verifica se a mesa está reservada"""
        return self.status == StatusMesa.RESERVADA

    @property
    def is_livre(self) -> bool:
        """Verifica se a mesa está livre"""
        return self.status == StatusMesa.LIVRE

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Gera número automaticamente se não fornecido
        if not self.numero and self.id:
            self.numero = f"M{self.id:03d}"