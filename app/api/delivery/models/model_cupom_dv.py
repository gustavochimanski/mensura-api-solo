from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed

# ----------------------
# CUPOM
# ----------------------
class CupomDescontoModel(Base):
    __tablename__ = "cupons_dv"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(30), unique=True, nullable=False)
    descricao = Column(String(120), nullable=True)

    desconto_valor = Column(Numeric(18, 2), nullable=True)
    desconto_percentual = Column(Numeric(5, 2), nullable=True)

    ativo = Column(Boolean, nullable=False, default=True)
    validade_inicio = Column(DateTime(timezone=True), nullable=True)
    validade_fim = Column(DateTime(timezone=True), nullable=True)

    monetizado = Column(Boolean, nullable=False, default=False)
    valor_por_lead = Column(Numeric(18, 2), nullable=True)

    parceiro_id = Column(Integer, ForeignKey("delivery.parceiros.id", ondelete="CASCADE"), nullable=False)
    parceiro = relationship("ParceiroModel", back_populates="cupons")

    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)

    pedidos = relationship(
        "PedidoDeliveryModel",
        back_populates="cupom",
        cascade="all, delete-orphan",
    )

    # Relação para os links
    links = relationship(
        "CupomLinkModel",
        back_populates="cupom",
        cascade="all, delete-orphan"
    )


# ----------------------
# LINKS DO CUPOM
# ----------------------
class CupomLinkModel(Base):
    __tablename__ = "cupons_links_dv"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    cupom_id = Column(Integer, ForeignKey("delivery.cupons_dv.id", ondelete="CASCADE"), nullable=False)
    titulo = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)

    cupom = relationship("CupomDescontoModel", back_populates="links")
    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)
