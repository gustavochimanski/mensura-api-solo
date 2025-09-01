from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.database.db_connection import Base

class ClienteOtpModel(Base):
    __tablename__ = "cliente_otp"

    id = Column(Integer, primary_key=True)
    telefone = Column(String(20), nullable=False)
    codigo = Column(String(6), nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    expira_em = Column(DateTime, nullable=False)
