from sqlalchemy import Column, Integer, String, Numeric, Date

from app.database.db_connection import Base


class Meta(Base):
    __tablename__ = "metas"
    __table_args__ = {"schema": "mensura"}

    mefi_codigo = Column(Integer, primary_key=True, autoincrement=True)
    mefi_codempresa = Column(String(3), nullable=False)
    mefi_descricao = Column(String(200), nullable=False)
    mefi_valor = Column(Numeric(18, 5), nullable=False)
    mefi_data = Column(Date, nullable=False)
