from pydantic import ConfigDict
from sqlalchemy import (
    Column, Integer, String, Numeric,
    ForeignKey, ForeignKeyConstraint,
    Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database.db_connection import Base

class ProdutosEmpDeliveryModel(Base):
    __tablename__ = "cadprod_emp_delivery"
    __table_args__ = (
        ForeignKeyConstraint(
            ["cod_barras"],
            ["mensura.cadprod_delivery.cod_barras"],
            name="fk_produto_empresa_cod_barras",
            ondelete="CASCADE"
        ),
        UniqueConstraint(
            "empresa", "cod_barras",
            name="uix_empresa_cod_barras"
        ),
        Index(
            "idx_empresa_produto",
            "empresa", "cod_barras"
        ),
        {"schema": "mensura"}
    )

    # Composite PK: empresa + cod_barras
    empresa = Column(Integer, ForeignKey("mensura.empresas.id"), primary_key=True)
    empresa_rel = relationship("EmpresaModel", back_populates="produtos")
    cod_barras = Column(String, primary_key=True, nullable=False)

    custo = Column(Numeric(18, 5), nullable=True)
    preco_venda = Column(Numeric(18, 5), nullable=False)

    # FK para subcategoria/vitrine
    subcategoria_id = Column(
        Integer,
        ForeignKey("mensura.vitrines.id", ondelete="SET NULL"),
        nullable=True
    )

    produto = relationship(
        "ProdutoDeliveryModel",
        back_populates="produtos_empresa"
    )
    sub_categoria = relationship(
        "SubCategoriaModel",
        back_populates="produtos",
        foreign_keys=[subcategoria_id]
    )

    model_config = ConfigDict(from_attributes=True)
