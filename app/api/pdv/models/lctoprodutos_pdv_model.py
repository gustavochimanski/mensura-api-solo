from sqlalchemy import Column, String, Date, Numeric, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class LctoProdutosPDV(Base):
    __tablename__ = "lctoprodutos_pdv"
    __table_args__ = {"schema": "pdv"}

    lcpr_codempresa  = Column(String(3), primary_key=True)
    lcpr_datamvto    = Column(Date, primary_key=True)
    lcpr_pdv         = Column(String(3), primary_key=True)
    lcpr_cupom       = Column(String(9), primary_key=True)
    lcpr_seriedcto   = Column(String(3), primary_key=True)

    lcpr_totalprodutos = Column(Numeric(18, 5))
    lcpr_totaldcto     = Column(Numeric(18, 5))
    lcpr_situacao      = Column(String(1))
    lcpr_statusvenda   = Column(String(1))
    lcpr_codvendedor   = Column(String(3))

    lcpr_datahora      = Column(String(19))      # <--- pode deixar se usado em outro lugar
    lcpr_datahoraemiss = Column(TIMESTAMP)       # <--- este é o certo para agrupamento por hora
