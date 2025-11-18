from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed

# Associação cupom-empresa
cupom_empresa_association = Table(
    "cupons_empresas",
    Base.metadata,
    Column("cupom_id", Integer, ForeignKey("cadastros.cupons_dv.id", ondelete="CASCADE"), primary_key=True),
    Column("empresa_id", Integer, ForeignKey("cadastros.empresas.id", ondelete="CASCADE"), primary_key=True),
    schema="cadastros",
)

# ----------------------
# CUPOM
# ----------------------
class CupomDescontoModel(Base):
    __tablename__ = "cupons_dv"
    __table_args__ = {"schema": "cadastros"}

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

    parceiro_id = Column(Integer, ForeignKey("cadastros.parceiros.id", ondelete="CASCADE"), nullable=True)
    parceiro = relationship("ParceiroModel", back_populates="cupons")

    empresas = relationship(
        "EmpresaModel",
        secondary=cupom_empresa_association,
        back_populates="cupons",
    )

    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)

    pedidos = relationship(
        "PedidoDeliveryModel",
        back_populates="cupom",
        cascade="all, delete-orphan",
    )

    link_redirecionamento = Column(String(500), nullable=True)
