from sqlalchemy import Column, Integer, String, Numeric, Date
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ProdutoModel(Base):
    __tablename__ = "cadprod"
    __table_args__ = {"schema": "public"}

    cadp_codigo = Column(Integer, primary_key=True, index=True)
    cadp_situacao = Column(String(1))
    cadp_descricao = Column(String(50))
    cadp_complemento = Column(String(30))
    cadp_codcategoria = Column(Integer)
    cadp_categoria = Column(String(50))
    cadp_codmarca = Column(Integer)
    cadp_marca = Column(String(50))
    cadp_diretivas = Column(String(30))
    cadp_dtcadastro = Column(Date)
    cadp_balanca = Column(String(1))
    cadp_codigobarra = Column(String(13))
    cadp_controlaestoque = Column(String(1))
    cadp_vincpreco = Column(Integer)
    cadp_pesoun = Column(Numeric(18, 5))
    cadp_pesoemb = Column(Numeric(18, 5))
    cadp_codvasilhame = Column(String(3))



