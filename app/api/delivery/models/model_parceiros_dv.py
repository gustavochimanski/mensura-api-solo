from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Numeric, DateTime
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class ParceiroModel(Base):
    __tablename__ = "parceiros"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, unique=True)
    ativo = Column(Boolean, nullable=False, default=False)

    banners = relationship("BannerParceiroModel", back_populates="parceiro", cascade="all, delete-orphan")
    cupom_links = relationship("CupomParceiroLinkModel", back_populates="parceiro")


class BannerParceiroModel(Base):
    __tablename__ = "parceiros_banner"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)

    parceiro_id = Column(Integer, ForeignKey("delivery.parceiros.id", ondelete="CASCADE"), nullable=False)
    parceiro = relationship("ParceiroModel", back_populates="banners")

    categoria_id = Column(Integer, ForeignKey("delivery.categoria_dv.id", ondelete="CASCADE"), nullable=False)
    categoria = relationship("CategoriaDeliveryModel", back_populates="banners")

    imagem = Column(String(255), nullable=True)
    ativo = Column(Boolean, nullable=False, default=False)
    tipo_banner = Column(String(1), nullable=False)  # "V" ou "H"

    @property
    def href_destino(self):
        return f"/categoria/{self.categoria.slug}" if self.categoria else "#"


class CupomParceiroLinkModel(Base):
    __tablename__ = "cupons_parceiros_links"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    cupom_id = Column(Integer, ForeignKey("delivery.cupons_dv.id", ondelete="CASCADE"), nullable=False)
    parceiro_id = Column(Integer, ForeignKey("delivery.parceiros.id", ondelete="CASCADE"), nullable=False)

    valor_por_indicacao = Column(Numeric(18, 2), nullable=False, default=0)
    link_whatsapp = Column(String(500), nullable=False)
    qr_code_base64 = Column(String, nullable=True)
    created_at = Column(DateTime, default=now_trimmed, nullable=False)

    cupom = relationship("CupomDescontoModel", back_populates="parceiro_links")
    parceiro = relationship("ParceiroModel", back_populates="cupom_links")
    contatos = relationship("ContatoParceiroModel", back_populates="cupom_parceiro_link", cascade="all, delete-orphan")


class ContatoParceiroModel(Base):
    __tablename__ = "contatos_parceiros"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    cupom_parceiro_link_id = Column(Integer, ForeignKey("delivery.cupons_parceiros_links.id", ondelete="CASCADE"), nullable=False)
    nome_cliente = Column(String(100), nullable=True)
    whatsapp_contato = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=now_trimmed, nullable=False)

    cupom_parceiro_link = relationship("CupomParceiroLinkModel", back_populates="contatos")
