# models/user.py
from sqlalchemy import Column, Integer, String, ARRAY
from app.database.db_connection import Base

class UserModel(Base):
    __tablename__ = "usuarios"
    __table_args__ = {"schema": "mensura"}

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    type_user = Column(String, nullable=False)
    empresas_liberadas = Column(ARRAY(Integer), nullable=False, default=list)
