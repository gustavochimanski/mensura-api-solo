# app/schemas/produtosDelivery/produtos_schema.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class CriarNovoProdutoRequest(BaseModel):
    cod_barras: str
    descricao: str
    cod_categoria: int
    vitrine_id: Optional[int] = None
    preco_venda: float
    custo: Optional[float] = None
    data_cadastro: Optional[datetime] = None
    imagem: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CriarNovoProdutoResponse(BaseModel):
    cod_barras: str
    descricao: Optional[str]
    cod_categoria: Optional[int]
    imagem: Optional[str]
    data_cadastro: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

# Schema interno de listagem paginada
class ProdutoListItem(BaseModel):
    cod_barras: str
    descricao: Optional[str]
    imagem: Optional[str]
    preco_venda: float
    custo: float
    cod_categoria: int
    label_categoria: str

    model_config = ConfigDict(from_attributes=True)

class ProdutosPaginadosResponse(BaseModel):
    data: List[ProdutoListItem]
    total: int
    page: int
    limit: int
    has_more: bool

    model_config = ConfigDict(from_attributes=True)
