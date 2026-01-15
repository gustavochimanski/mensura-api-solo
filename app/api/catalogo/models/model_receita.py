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
    ingredientes = relationship(
        "ReceitaIngredienteModel",
        primaryjoin="ReceitaModel.id == ReceitaIngredienteModel.receita_id",
        foreign_keys="[ReceitaIngredienteModel.receita_id]",
        back_populates="receita",
        cascade="all, delete-orphan"
    )
    # DEPRECATED: Usar complementos ao invés de adicionais diretos
    adicionais = relationship("ReceitaAdicionalModel", back_populates="receita", cascade="all, delete-orphan")
    # NOVO: Complementos que contêm adicionais
    complementos = relationship(
        "ComplementoModel",
        secondary="catalogo.receita_complemento_link",
        back_populates="receitas",
        viewonly=True,  # Leitura apenas, pois a relação real é no link
    )


class ReceitaIngredienteModel(Base):
    """
    Modelo de Ingrediente de Receita - Relacionamento N:N 
    
    Suporta múltiplos tipos de itens:
    1. Ingredientes básicos (ingrediente_id preenchido)
    2. Sub-receitas (receita_ingrediente_id preenchido)
    3. Produtos normais (produto_cod_barras preenchido)
    4. Combos (combo_id preenchido)
    
    A constraint CHECK garante que exatamente um dos quatro campos seja preenchido.
    """
    __tablename__ = "receita_ingrediente"
    __table_args__ = (
        {"schema": "catalogo"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    receita_id = Column(Integer, ForeignKey("catalogo.receitas.id", ondelete="CASCADE"), nullable=False)
    
    # Tipos de itens (mutuamente exclusivos - exatamente um deve ser preenchido)
    ingrediente_id = Column(Integer, ForeignKey("catalogo.ingredientes.id", ondelete="RESTRICT"), nullable=True)
    receita_ingrediente_id = Column(Integer, ForeignKey("catalogo.receitas.id", ondelete="RESTRICT"), nullable=True)
    produto_cod_barras = Column(String, ForeignKey("catalogo.produtos.cod_barras", ondelete="RESTRICT"), nullable=True)
    combo_id = Column(Integer, ForeignKey("catalogo.combos.id", ondelete="RESTRICT"), nullable=True)
    
    quantidade = Column(Numeric(18, 4), nullable=True)

    # Relacionamentos
    receita = relationship("ReceitaModel", foreign_keys=[receita_id], back_populates="ingredientes")
    ingrediente = relationship("IngredienteModel", back_populates="receitas_ingrediente")
    receita_ingrediente = relationship("ReceitaModel", foreign_keys=[receita_ingrediente_id])
    produto = relationship("ProdutoModel", foreign_keys=[produto_cod_barras])
    combo = relationship("ComboModel", foreign_keys=[combo_id])


class ReceitaAdicionalModel(Base):
    """
    Modelo de Adicional de Receita
    
    DEPRECATED: Este modelo está obsoleto. 
    Agora receitas devem usar complementos que contêm adicionais.
    Use receita_complemento_link para vincular complementos a receitas.
    Mantido apenas para compatibilidade com dados legados.
    """
    __tablename__ = "receita_adicional"
    __table_args__ = ({"schema": "catalogo"},)

    id = Column(Integer, primary_key=True, autoincrement=True)
    receita_id = Column(Integer, ForeignKey("catalogo.receitas.id", ondelete="CASCADE"), nullable=False)
    adicional_id = Column(Integer, ForeignKey("catalogo.adicionais.id", ondelete="RESTRICT"), nullable=False)

    receita = relationship("ReceitaModel", back_populates="adicionais")
    adicional = relationship("AdicionalModel", foreign_keys=[adicional_id])

