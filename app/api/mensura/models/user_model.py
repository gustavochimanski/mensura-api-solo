# models/user.py
from sqlalchemy import Column, Integer, String, ARRAY
from sqlalchemy.orm import relationship

from app.api.mensura.models.association_tables import usuario_empresa
from app.database.db_connection import Base

class UserModel(Base):
    __tablename__ = "usuarios"
    __table_args__ = {"schema": "mensura"}

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    type_user = Column(String, nullable=False)
    empresas = relationship(
        "EmpresaModel",
        secondary=usuario_empresa,
        back_populates="usuarios"
    )

