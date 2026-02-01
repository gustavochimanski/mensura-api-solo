from pydantic import ConfigDict
from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, func
from sqlalchemy.orm import relationship
from app.database.db_connection import Base

class ProdutoModel(Base):
    __tablename__ = "produtos"
    __table_args__ = {"schema": "catalogo"}

    # PK técnica (estável). `cod_barras` vira atributo de negócio.
    id = Column(Integer, primary_key=True, autoincrement=True)
    cod_barras = Column(String, unique=True, index=True, nullable=False)
    descricao = Column(String(255), nullable=False)
    imagem = Column(String(255), nullable=True)
    data_cadastro = Column(Date, nullable=True)

    # extras úteis para cardápio
    ativo = Column(Boolean, nullable=False, default=True)
    unidade_medida = Column(String(10), nullable=True)  # ex: "UN", "KG"
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    # diretivas removido

    # Relacionamentos
    produtos_empresa = relationship("ProdutoEmpModel", back_populates="produto", cascade="all, delete-orphan")
    
    # Relacionamento N:N com complementos
    complementos = relationship(
        "ComplementoModel",
        secondary="catalogo.produto_complemento_link",
        back_populates="produtos",
        viewonly=True,
    )
    
    # Relacionamento N:N com adicionais (DEPRECADO - usar complementos)
    # Mantido apenas para compatibilidade durante migração
    # adicionais = relationship(
    #     "AdicionalModel",
    #     secondary="catalogo.produto_adicional_link",
    #     viewonly=True,
    # )
    
    # Relacionamento N:N com vitrines (global, sem separação por empresa)
    vitrines = relationship(
        "VitrinesModel",
        secondary="cardapio.vitrine_produto",
        back_populates="produtos",
        viewonly=True,
    )

    model_config = ConfigDict(from_attributes=True)

