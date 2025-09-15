# app/api/mensura/schemas/schema_impressora.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any

class ImpressoraConfig(BaseModel):
    nome_impressora: Optional[str] = None
    fonte_nome: str = "Courier New"
    fonte_tamanho: int = 24
    espacamento_linha: int = 40
    espacamento_item: int = 50
    nome_estabelecimento: str = ""
    mensagem_rodape: str = "Obrigado pela preferencia!"
    formato_preco: str = "R$ {:.2f}"
    formato_total: str = "TOTAL: R$ {:.2f}"

class ImpressoraBase(BaseModel):
    nome: str
    nome_impressora: Optional[str] = None
    config: ImpressoraConfig = Field(default_factory=ImpressoraConfig)

class ImpressoraCreate(ImpressoraBase):
    empresa_id: int

class ImpressoraUpdate(BaseModel):
    nome: Optional[str] = None
    nome_impressora: Optional[str] = None
    config: Optional[ImpressoraConfig] = None

class ImpressoraResponse(ImpressoraBase):
    id: int
    empresa_id: int
    empresa_nome: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
