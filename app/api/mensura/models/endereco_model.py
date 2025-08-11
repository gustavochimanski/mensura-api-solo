# app/api/mensura/models/endereco_model.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from pydantic import ConfigDict

from app.database.db_connection import Base


class EnderecoModel(Base):
    __tablename__ = "enderecos"
    __table_args__ = {"schema": "mensura"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    cep = Column(String(10), nullable=True)
    logradouro = Column(String(100), nullable=True)
    numero = Column(String(10), nullable=True)
    complemento = Column(String(50), nullable=True)
    bairro = Column(String(50), nullable=True)
    cidade = Column(String(50), nullable=True)
    estado = Column(String(2), nullable=True)

    empresa = relationship("EmpresaModel", back_populates="endereco", uselist=False)

    model_config = ConfigDict(from_attributes=True)
