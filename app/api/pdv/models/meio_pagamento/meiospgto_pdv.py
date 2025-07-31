from sqlalchemy import Column, String
from app.database.db_connection import Base


class MeiosPgtoPDVModel(Base):
    __tablename__ = "meiospgto_pdv"
    __table_args__ = {"schema": "pdv"}

    mpgt_codigo    = Column(String(3), nullable=True)
    mpgt_descricao = Column(String(20), nullable=True)
    mpgt_tipo      = Column(String(2), nullable=True)
    mpgt_idecf     = Column(String(2), nullable=True)
    mpgt_diretivas = Column(String(2000), nullable=True)
