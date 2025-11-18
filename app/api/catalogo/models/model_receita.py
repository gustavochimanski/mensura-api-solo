from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from decimal import Decimal

from app.database.db_connection import Base


class ReceitaModel(Base):
    """Modelo de Receita - Entidade no schema catalogo"""
    __tablename__ = "receitas"
    __table_args__ = ({"schema": "catalogo"},)

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(100), nullable=False)
    descricao = Column(String(255), nullable=True)
    preco_venda = Column(Numeric(18, 2), nullable=False)
    imagem = Column(String(500), nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    disponivel = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    ingredientes = relationship("ReceitaIngredienteModel", back_populates="receita", cascade="all, delete-orphan")
    adicionais = relationship("ReceitaAdicionalModel", back_populates="receita", cascade="all, delete-orphan")


class ReceitaIngredienteModel(Base):
    """Modelo de Ingrediente de Receita - Relacionamento N:N (ingrediente pode estar em várias receitas)"""
    __tablename__ = "receita_ingrediente"
    __table_args__ = (
        {"schema": "catalogo"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    receita_id = Column(Integer, ForeignKey("catalogo.receitas.id", ondelete="CASCADE"), nullable=False)
    ingrediente_id = Column(Integer, ForeignKey("catalogo.ingredientes.id", ondelete="RESTRICT"), nullable=False)
    quantidade = Column(Numeric(18, 4), nullable=True)

    receita = relationship("ReceitaModel", back_populates="ingredientes")
    ingrediente = relationship("IngredienteModel", back_populates="receitas_ingrediente")


class ReceitaAdicionalModel(Base):
    """Modelo de Adicional de Receita"""
    __tablename__ = "receita_adicional"
    __table_args__ = ({"schema": "catalogo"},)

    id = Column(Integer, primary_key=True, autoincrement=True)
    receita_id = Column(Integer, ForeignKey("catalogo.receitas.id", ondelete="CASCADE"), nullable=False)
    adicional_cod_barras = Column(String, ForeignKey("catalogo.produtos.cod_barras", ondelete="RESTRICT"), nullable=False)
    # preco removido - sempre busca do ProdutoEmpModel em tempo de execução

    receita = relationship("ReceitaModel", back_populates="adicionais")
    adicional = relationship("ProdutoModel", foreign_keys=[adicional_cod_barras])

