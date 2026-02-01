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
    # Complementos que contêm adicionais
    complementos = relationship(
        "ComplementoModel",
        secondary="catalogo.combo_complemento_link",
        back_populates="combos",
        viewonly=True,  # Leitura apenas, pois a relação real é no link
    )

    model_config = ConfigDict(from_attributes=True)


class ComboItemModel(Base):
    """
    Modelo de Item de Combo - Relacionamento N:N
    
    Suporta dois tipos de itens:
    1. Produtos normais (produto_cod_barras preenchido)
    2. Receitas (receita_id preenchido)
    
    A constraint CHECK garante que exatamente um dos dois campos seja preenchido.
    """
    __tablename__ = "combos_itens"
    __table_args__ = {"schema": "catalogo"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    combo_id = Column(Integer, ForeignKey("catalogo.combos.id", ondelete="CASCADE"), nullable=False)
    
    # Tipos de itens (mutuamente exclusivos - exatamente um deve ser preenchido)
    # Novo: FK técnica para produto
    produto_id = Column(Integer, ForeignKey("catalogo.produtos.id", ondelete="RESTRICT"), nullable=True)
    # Legado/compatibilidade: código de barras armazenado como atributo (sem FK)
    produto_cod_barras = Column(String, nullable=True)
    receita_id = Column(Integer, ForeignKey("catalogo.receitas.id", ondelete="RESTRICT"), nullable=True)
    
    quantidade = Column(Integer, nullable=False, default=1)

    combo = relationship("ComboModel", back_populates="itens")
    produto = relationship("ProdutoModel", foreign_keys=[produto_id])
    receita = relationship("ReceitaModel", foreign_keys=[receita_id])

    model_config = ConfigDict(from_attributes=True)

