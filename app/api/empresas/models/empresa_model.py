# app/api/empresas/models/empresa_model.py
from sqlalchemy import Column, Integer, String, Boolean, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from pydantic import ConfigDict

from app.api.cadastros.models.association_tables import entregador_empresa, usuario_empresa
from app.database.db_connection import Base


class EmpresaModel(Base):
    __tablename__ = "empresas"
    __table_args__ = {"schema": "cadastros"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    cnpj = Column(String(20), nullable=True, unique=True)
    slug = Column(String(50), nullable=False, unique=True)
    logo = Column(String(255), nullable=True)
    telefone = Column(String(255), nullable=True)

    aceita_pedido_automatico = Column(Boolean, nullable=False, default=False)

    # Horário de funcionamento (para chatbot e disponibilidade)
    # Estrutura esperada (JSON):
    # [
    #   {"dia_semana": 0..6, "intervalos": [{"inicio":"HH:MM","fim":"HH:MM"}]}
    # ]
    # dia_semana: 0=domingo, 1=segunda, ..., 6=sábado
    timezone = Column(String(64), nullable=True, default="America/Sao_Paulo")
    horarios_funcionamento = Column(JSONB, nullable=True)

    # Configurações de Cardápio
    cardapio_link = Column(String(255), nullable=True, unique=True)
    cardapio_tema = Column(String(50), nullable=True, default="padrao")
    tempo_entrega_maximo = Column(Integer, nullable=False, default=60)  # minutos

    cep = Column(String(10), nullable=True)
    logradouro = Column(String(120), nullable=True)
    numero = Column(String(20), nullable=True)
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(80), nullable=True)
    cidade = Column(String(80), nullable=True)
    estado = Column(String(2), nullable=True)
    ponto_referencia = Column(String(100), nullable=True)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)

    # Relationships
    produtos_emp = relationship(
        "ProdutoEmpModel",
        back_populates="empresa"
    )
    pedidos = relationship(
        "PedidoUnificadoModel",
        back_populates="empresa",
        cascade="all, delete-orphan"
    )
    cupons = relationship(
        "CupomDescontoModel",
        secondary="cadastros.cupons_empresas",  # Tabela de associação fica em cadastros
        back_populates="empresas",
    )
    entregadores = relationship(
        "EntregadorDeliveryModel",
        secondary=entregador_empresa,
        back_populates="empresas"
    )
    usuarios = relationship(
        "UserModel",
        secondary=usuario_empresa,
        back_populates="empresas"
    )
    regioes_entrega = relationship(
        "RegiaoEntregaModel",
        back_populates="empresa"
    )
    
    caixas = relationship(
        "CaixaModel",
        back_populates="empresa",
        cascade="all, delete-orphan"
    )

    model_config = ConfigDict(from_attributes=True)

