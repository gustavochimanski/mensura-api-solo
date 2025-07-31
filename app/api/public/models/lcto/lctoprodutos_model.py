# app/api/public/models/lcto/lctoprodutos_model.py
from sqlalchemy import Column, String, Date, Numeric
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class LctoProdutosPUBLIC(Base):
    __tablename__ = "lctoprodutos"
    __table_args__ = {"schema": "public"}

    # chaves primárias originais
    lcpr_codempresa  = Column(String(3), primary_key=True)
    lcpr_dtmvto      = Column(Date,   primary_key=True)
    lcpr_pdv         = Column(String(3), primary_key=True)
    lcpr_cupom       = Column(String(9), primary_key=True)
    lcpr_seriedcto   = Column(String(3), primary_key=True)

    # colunas usadas nas suas consultas detalhadas
    lcpr_totalprodutos = Column(Numeric(18,5))
    lcpr_desconto      = Column(Numeric(18,5))
    lcpr_acrescimopdv  = Column(Numeric(18,5))
