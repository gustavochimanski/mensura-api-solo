from sqlalchemy import Column, String, Integer, Numeric
from app.database.db_connection import Base

class CategoriaProdutoPublicModel(Base):
    __tablename__ = "categoriaprod"
    __table_args__ = {"schema": "public"}

    cate_codigo               = Column(Integer, index=True)
    cate_classificacao        = Column(String(30), nullable=True)
    cate_descricao            = Column(String(50), nullable=True)
    cate_tipo                 = Column(String(2), nullable=True)
    cate_codsubempresa        = Column(Integer, index=True)
