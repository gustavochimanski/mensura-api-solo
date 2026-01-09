from pydantic import ConfigDict
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database.db_connection import Base


class ComboModel(Base):
    __tablename__ = "combos"
    __table_args__ = (
        {"schema": "catalogo"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id", ondelete="RESTRICT"), nullable=False)
    titulo = Column(String(120), nullable=True)
    descricao = Column(String(255), nullable=False)
    imagem = Column(String(255), nullable=True)
    preco_total = Column(Numeric(18, 2), nullable=False)
    custo_total = Column(Numeric(18, 2), nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    itens = relationship("ComboItemModel", back_populates="combo", cascade="all, delete-orphan")
    empresa = relationship("EmpresaModel")

    model_config = ConfigDict(from_attributes=True)


class ComboItemModel(Base):
    __tablename__ = "combos_itens"
    __table_args__ = {"schema": "catalogo"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    combo_id = Column(Integer, ForeignKey("catalogo.combos.id", ondelete="CASCADE"), nullable=False)
    produto_cod_barras = Column(String, ForeignKey("catalogo.produtos.cod_barras", ondelete="RESTRICT"), nullable=False)
    quantidade = Column(Integer, nullable=False, default=1)

    combo = relationship("ComboModel", back_populates="itens")
    produto = relationship("ProdutoModel")

    model_config = ConfigDict(from_attributes=True)

