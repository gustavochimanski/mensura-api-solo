from sqlalchemy import Column, String, Date, Integer, Numeric
from app.database.db_connection import Base


class MovMeioPgtoPDVModel(Base):
    __tablename__ = "movmeiopgto_pdv"
    __table_args__ = {"schema": "pdv"}

    movm_numabertura   = Column(String(16), nullable=True)
    movm_datamvto      = Column(Date, nullable=False, primary_key=True)
    movm_cupom         = Column(String(9), nullable=False, primary_key=True)
    movm_situacao      = Column(String(1), nullable=True)
    movm_codempresa    = Column(String(3), nullable=False, primary_key=True)
    movm_pdv           = Column(String(3), nullable=False, primary_key=True)
    movm_ecf           = Column(String(3), nullable=True)
    movm_seq           = Column(Integer, nullable=False, primary_key=True)
    movm_codmeiopgto   = Column(String(3), nullable=True)
    movm_tipo          = Column(Integer, nullable=True)
    movm_valor         = Column(Numeric(18, 5), nullable=True)
    movm_troco         = Column(Numeric(18, 5), nullable=True)
    movm_codentidade   = Column(Integer, nullable=True)
    movm_mpgtotroco    = Column(String(2), nullable=True)
    movm_gnf           = Column(String(9), nullable=True)
    movm_ccf           = Column(String(9), nullable=True)
    movm_saque         = Column(Numeric(18, 5), nullable=True)
    movm_idscashback   = Column(String(500), nullable=True)
    movm_tipomvto      = Column(String(3), nullable=True)
    movm_bin           = Column(String(10), nullable=True)
    movm_fcconf        = Column(String(1), nullable=True)
