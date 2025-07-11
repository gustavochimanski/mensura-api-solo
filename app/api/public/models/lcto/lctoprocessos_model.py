from sqlalchemy import Column, String, Date, Integer, Numeric, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class LctoProcesso(Base):
    __tablename__ = "lctoprocessos"
    __table_args__ = {"schema": "public"}

    lamp_protocolo = Column(String(16), primary_key=True)
    lamp_chave = Column(String(16))
    lamp_situacao = Column(String(1))
    lamp_codprocesso = Column(String(4))
    lamp_tipoprocesso = Column(String(2))
    lamp_dtlcto = Column(Date)
    lamp_dtmvto = Column(Date)
    lamp_valor = Column(Numeric(18, 5))
    lamp_codusuario = Column(String(4))
    lamp_codempresa = Column(String(3))
    lamp_dcto = Column(Integer)
    lamp_codusucancelamento = Column(String(4))
    lamp_dtcancelamento = Column(TIMESTAMP)
    lamp_motivocancelamento = Column(String(100))
    lamp_codentidade = Column(Integer)
    lamp_codespecie = Column(String(4))
    lamp_codusuauditoria = Column(String(4))
    lamp_dtauditoria = Column(Date)
    lamp_modelodcto = Column(String(3))
    lamp_codgabarito = Column(String(3))
    lamp_numerogabarito = Column(Integer)
    lamp_idlcto = Column(String(9))
    lamp_codgeradorfin = Column(String(3))
    lamp_lote = Column(Integer)
    lamp_dthoramvto = Column(TIMESTAMP)
    lamp_protocoloorigem = Column(String(16))
    lamp_protocolochave = Column(String(16))
    lamp_reservado = Column(String(5000))
