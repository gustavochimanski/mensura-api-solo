# app/api/mensura/models/categoria_model.py
from typing import Optional
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class CategoriaModel(Base):
    __tablename__ = "categorias"
    __table_args__ = {"schema": "cadastros"}

    id = Column(Integer, primary_key=True)
    descricao = Column(String(100), nullable=False)
    ativo = Column(Integer, nullable=False, default=1)  # 1=ativo, 0=inativo

    parent_id = Column(Integer, ForeignKey("cadastros.categorias.id", ondelete="SET NULL"), nullable=True)
    parent = relationship("CategoriaModel", remote_side=[id], back_populates="children")
    children = relationship("CategoriaModel", back_populates="parent", cascade="all, delete-orphan")

    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)

    # Relacionamento com produtos
    # produtos = relationship("ProdutoModel", back_populates="categoria")  # Removido

    @hybrid_property
    def is_active(self) -> bool:
        return self.ativo == 1

    @property
    def label(self) -> str:
        return self.descricao
