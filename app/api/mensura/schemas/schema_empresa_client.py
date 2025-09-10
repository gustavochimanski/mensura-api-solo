# app/api/mensura/schemas/schema_empresa.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from app.api.mensura.schemas.schema_endereco import EnderecoResponse, EnderecoCreate

class EmpresaOut(BaseModel):
    nome: str
    logo: Optional[str] = None
    cardapio_tema: Optional[str] = "padrao"
    aceita_pedido_automatico: bool = False
    tempo_entrega_maximo: int = Field(..., gt=0)
