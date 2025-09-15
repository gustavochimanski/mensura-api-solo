# app/api/mensura/models/impressora_model.py
from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from pydantic import ConfigDict

from app.database.db_connection import Base


class ImpressoraModel(Base):
    __tablename__ = "impressoras"
    __table_args__ = {"schema": "mensura"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    
    # Configurações da impressora
    config = Column(JSON, nullable=False, default={
        "nome_impressora": None,
        "fonte_nome": "Courier New",
        "fonte_tamanho": 24,
        "espacamento_linha": 40,
        "espacamento_item": 50,
        "nome_estabelecimento": "",
        "mensagem_rodape": "Obrigado pela preferencia!",
        "formato_preco": "R$ {:.2f}",
        "formato_total": "TOTAL: R$ {:.2f}"
    })
    
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
