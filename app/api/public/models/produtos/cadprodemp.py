# app/api/public/models/produto_empresa_model.py

from sqlalchemy import Column, Integer, String, Numeric
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ProdutoEmpresaModel(Base):
    __tablename__ = "cadprodemp"
    __table_args__ = {"schema": "public"}

    # ———————————————— Chaves primárias ————————————————
    cade_codigo      = Column(Integer, primary_key=True, index=True)
    cade_codempresa  = Column(String(3))
    cade_prvenda     = Column(Numeric(18, 5))

