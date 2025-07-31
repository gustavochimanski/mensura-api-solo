# app/models/empresa_model.py
from sqlalchemy import Column, String, Integer, Date
from app.database.db_connection import Base  # certifique-se de ter o Base

class Empresa(Base):
    __tablename__ = "empresas"
    __table_args__ = {"schema": "public"}

    empr_codigo = Column(String(3), primary_key=True)
    empr_nome = Column(String(100))
    empr_endereco = Column(String(100))
    empr_numero = Column(Integer)
    empr_bairro = Column(String(20))
    empr_codmunicipio = Column(String(4))
    empr_municipio = Column(String(50))
    empr_uf = Column(String(2))
    empr_cep = Column(String(8))
    empr_fone = Column(String(13))
    empr_situacao = Column(String(1))  # Aqui deve ser "A" ou "I" (ativo/inativo)
