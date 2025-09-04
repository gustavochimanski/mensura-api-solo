from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy
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
    minimo_compra = Column(Numeric(18, 2), nullable=True)

    monetizado = Column(Boolean, nullable=False, default=False)
    valor_por_lead = Column(Numeric(18, 2), nullable=True)

    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)

    # Relação com parceiros via link
    parceiro_links = relationship("CupomParceiroLinkModel", back_populates="cupom", cascade="all, delete-orphan")

    # Proxy para acessar todos os contatos de um cupom direto
    contatos = association_proxy("parceiro_links", "contatos")

    @property
    def link_whatsapp(self) -> str | None:
        if not self.monetizado or not self.parceiro_links:
            return None
        parceiro = self.parceiro_links[0].parceiro
        return f"https://api.whatsapp.com/send?text=Olá! Vim pelo {parceiro.nome}. Código do cupom: {self.codigo}"

