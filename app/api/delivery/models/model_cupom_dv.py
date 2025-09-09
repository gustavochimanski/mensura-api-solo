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

    @property
    def link_whatsapp(self) -> str | None:
        """
        Gera link de WhatsApp usando o telefone do parceiro.
        Exemplo: https://wa.me/5511999999999?text=...
        """
        if not self.monetizado or not self.parceiro or not self.parceiro.telefone:
            return None

        telefone = self.parceiro.telefone.strip().replace(" ", "").replace("-", "")
        texto = f"Olá! Vim pelo parceiro {self.parceiro.nome}. Código do cupom: {self.codigo}"
        return f"https://wa.me/{telefone}?text={texto}"
