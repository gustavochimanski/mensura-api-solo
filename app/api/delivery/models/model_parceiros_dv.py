from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed

# ----------------------
# LINK CUPOM-PARCEIRO
# ----------------------
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

    # Relação com contatos
    contatos = relationship("ContatoParceiroModel", back_populates="cupom_parceiro_link", cascade="all, delete-orphan")


# ----------------------
# CONTATO DO PARCEIRO
# ----------------------
class ContatoParceiroModel(Base):
    __tablename__ = "parceiros_contatos"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    cupom_parceiro_link_id = Column(Integer, ForeignKey("delivery.cupons_parceiros_links.id", ondelete="CASCADE"), nullable=False)
    nome_cliente = Column(String(100), nullable=True)
    whatsapp_contato = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=now_trimmed, nullable=False)

    cupom_parceiro_link = relationship("CupomParceiroLinkModel", back_populates="contatos")