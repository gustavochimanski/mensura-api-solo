from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from pydantic import ConfigDict

class EmpresaModel(Base):
    __tablename__ = "empresas"
    __table_args__ = {"schema": "mensura"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    cnpj = Column(String(20), nullable=True, unique=True)
    slug = Column(String(50), nullable=False, unique=True)
    logo = Column(String(255), nullable=True)

    # Novo campo de endereço
    endereco_id = Column(
        Integer,
        ForeignKey("mensura.enderecos.id", ondelete="SET NULL"),
        nullable=True
    )
    endereco = relationship("EnderecoModel", back_populates="empresa")

    # Relacionamentos
    produtos_emp = relationship("ProdutosEmpDeliveryModel", back_populates="empresa_rel")
    vitrines = relationship("VitrinesModel", back_populates="empresa_rel")

    model_config = ConfigDict(from_attributes=True)
