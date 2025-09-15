# app/api/mensura/schemas/schema_impressora.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any

class ImpressoraConfigData(BaseModel):
    nome_impressora: Optional[str] = None
    fonte_nome: str = "Courier New"
    fonte_tamanho: int = 24
    espacamento_linha: int = 40
    espacamento_item: int = 50
    mensagem_rodape: str = "Obrigado pela preferencia!"
    formato_preco: str = "R$ {:.2f}"
    formato_total: str = "TOTAL: R$ {:.2f}"

class EmpresaConfigData(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    telefone: Optional[str] = None

class ConfigResponse(BaseModel):
    impressora: ImpressoraConfigData
    empresa: EmpresaConfigData

class ImpressoraBase(BaseModel):
    nome: str
    config: ImpressoraConfigData = Field(default_factory=ImpressoraConfigData)

class ImpressoraCreate(ImpressoraBase):
    empresa_id: int

class ImpressoraUpdate(BaseModel):
    nome: Optional[str] = None
    config: Optional[ImpressoraConfigData] = None

class ImpressoraResponse(BaseModel):
    id: int
    nome: str
    empresa_id: int
    empresa_nome: Optional[str] = None
    config: ConfigResponse

    model_config = ConfigDict(from_attributes=True)
