from sqlalchemy import Column, String, Integer
from app.database.db_connection import Base


class MeiosPgtoPublicModel(Base):
    __tablename__ = "meiospagamento"
    __table_args__ = {"schema": "public"}

    mpgt_codigo    = Column(String(3), primary_key=True)
    mpgt_descricao = Column(String(20), nullable=True)
    mpgt_tpmeiopgto     = Column(String(2), nullable=True)
    mpgt_codfinaliz = Column(Integer)
