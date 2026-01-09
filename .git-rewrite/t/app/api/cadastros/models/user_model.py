# app/api/mensura/models/user_model.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.api.cadastros.models.association_tables import usuario_empresa
from app.database.db_connection import Base


class UserModel(Base):
    __tablename__ = "usuarios"
    __table_args__ = {"schema": "cadastros"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    type_user = Column(String(30), nullable=False)

    empresas = relationship(
        "EmpresaModel",
        secondary=usuario_empresa,
        back_populates="usuarios",
    )
