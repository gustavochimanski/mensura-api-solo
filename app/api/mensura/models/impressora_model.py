# app/api/mensura/models/impressora_model.py
from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from pydantic import ConfigDict

from app.database.db_connection import Base


class ImpressoraModel(Base):
    __tablename__ = "impressoras"
    __table_args__ = {"schema": "mensura"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    
    # Configurações da impressora - cada campo em sua própria coluna
    nome_impressora = Column(String(100), nullable=True)
    fonte_nome = Column(String(50), nullable=False, default="Courier New")
    fonte_tamanho = Column(Integer, nullable=False, default=24)
    espacamento_linha = Column(Integer, nullable=False, default=40)
    espacamento_item = Column(Integer, nullable=False, default=50)
    nome_estabelecimento = Column(String(100), nullable=False, default="")
    mensagem_rodape = Column(Text, nullable=False, default="Obrigado pela preferencia!")
    formato_preco = Column(String(50), nullable=False, default="R$ {:.2f}")
    formato_total = Column(String(50), nullable=False, default="TOTAL: R$ {:.2f}")
    
    empresa_id = Column(
        Integer,
        ForeignKey("mensura.empresas.id", ondelete="CASCADE"),
        nullable=False
    )

    # Relationships
    empresa = relationship(
        "EmpresaModel",
        back_populates="impressoras"
    )

    model_config = ConfigDict(from_attributes=True)
