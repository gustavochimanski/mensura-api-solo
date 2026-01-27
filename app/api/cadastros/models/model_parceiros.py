from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.db_connection import Base


# ----------------------
# PARCEIRO
# ----------------------
class ParceiroModel(Base):
    __tablename__ = "parceiros"
    __table_args__ = {"schema": "cadastros"}

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, unique=True)
    ativo = Column(Boolean, nullable=False, default=False)
    telefone = Column(String(20), nullable=True)

    banners = relationship("BannerParceiroModel", back_populates="parceiro", cascade="all, delete-orphan")
    cupons = relationship("CupomDescontoModel", back_populates="parceiro", cascade="all, delete-orphan")


class BannerParceiroModel(Base):
    __tablename__ = "parceiros_banner"
    __table_args__ = {"schema": "cadastros"}

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)

    parceiro_id = Column(Integer, ForeignKey("cadastros.parceiros.id", ondelete="CASCADE"), nullable=False)
    parceiro = relationship("ParceiroModel", back_populates="banners")

    categoria_id = Column(Integer, ForeignKey("cardapio.categoria_dv.id", ondelete="CASCADE"), nullable=True)
    categoria = relationship("CategoriaDeliveryModel", back_populates="banners")

    imagem = Column(String(255), nullable=True)
    ativo = Column(Boolean, nullable=False, default=False)
    tipo_banner = Column(String(1), nullable=False)  # "V" ou "H"
    landingpage_store = Column(Boolean, nullable=False, default=False)
    link_redirecionamento = Column(String(255), nullable=True)

    @property
    def href_destino(self):
        # Se houver link explícito, usa-o
        if self.link_redirecionamento:
            return self.link_redirecionamento
        return "#"
