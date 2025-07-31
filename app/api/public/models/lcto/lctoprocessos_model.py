# app/models/lcto_processos.py
from sqlalchemy import Column, String, Date, Numeric
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class LctoProcesso(Base):
    __tablename__ = "lctoprocessos"
    __table_args__ = {"schema": "public"}

    # PKs mínimas
    lamp_protocolo    = Column(String(16), primary_key=True)
    lamp_chave        = Column(String(16), primary_key=True)
    lamp_dtmvto       = Column(Date,       primary_key=True)
    lamp_codempresa   = Column(String(3),  primary_key=True)
    lamp_tipoprocesso = Column(String(2),  primary_key=True)

    # coluna que você soma / filtra
    lamp_valor        = Column(Numeric(18, 5))
