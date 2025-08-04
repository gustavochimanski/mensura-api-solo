from sqlalchemy import Column, String, Integer, Numeric
from app.database.db_connection import Base

class SubEmpresaPublicModel(Base):
    __tablename__ = "subempresas"
    __table_args__ = {"schema": "public"}

    sube_classificacao = Column(String(30), nullable=True)
    sube_descricao     = Column(String(50), nullable=True)
    sube_codigo        = Column(Integer, index=True)  # índice na DDL
    sube_vendas        = Column(String(1), nullable=True)
    sube_lucroestimado = Column(Numeric(18, 5), nullable=True)