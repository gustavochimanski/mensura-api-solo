from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed

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
    minimo_compra = Column(Numeric(18, 2), nullable=True)

    # --- monetização ---
    monetizado = Column(Boolean, nullable=False, default=False)
    parceiro_id = Column(Integer, ForeignKey("delivery.parceiros.id", ondelete="SET NULL"), nullable=True)
    valor_por_lead = Column(Numeric(18, 2), nullable=True)

    parceiro = relationship("ParceiroModel")

    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)

    pedidos = relationship("PedidoDeliveryModel", back_populates="cupom")

    @property
    def link_whatsapp(self) -> str | None:
        if not self.monetizado or not self.parceiro:
            return None
        texto = f"Olá! Vim pelo {self.parceiro.nome}. Código do cupom: {self.codigo}"
        return f"https://api.whatsapp.com/send?text={texto}"
