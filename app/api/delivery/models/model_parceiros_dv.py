# app/api/delivery/models/model_parceiros_dv.py
from typing import Optional, List
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database.db_connection import Base

class ParceiroModel(Base):
    __tablename__ = "parceiros"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, unique=True)
    ativo = Column(Boolean, nullable=False, default=False)

    banners = relationship("BannerParceiroModel", back_populates="parceiro", cascade="all, delete-orphan")


class BannerParceiroModel(Base):
    __tablename__ = "parceiros_banner"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    parceiro_id = Column(Integer, ForeignKey("delivery.parceiros.id", ondelete="CASCADE"), nullable=False)
    imagem = Column(String(255), nullable=True)
    ativo = Column(Boolean, nullable=False, default=False)
    tipo_banner = Column(String(1), nullable=False)  # "V" ou "H"

    parceiro = relationship("ParceiroModel", back_populates="banners")
