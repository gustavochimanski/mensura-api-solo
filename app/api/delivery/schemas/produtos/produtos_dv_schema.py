# app/api/delivery/schemas/produtos_dv_schema.py
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class CriarNovoProdutoRequest(BaseModel):
    cod_barras: str
    descricao: str
    cod_categoria: int
    imagem: Optional[str] = None
    data_cadastro: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class CriarNovoProdutoResponse(BaseModel):
    cod_barras: str
    descricao: str
    cod_categoria: int
    imagem: Optional[str] = None
    data_cadastro: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ProdutoListItem(BaseModel):
    cod_barras: str
    descricao: str
    imagem: Optional[str] = None
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

class ProdutoEmpDTO(BaseModel):
    empresa_id: int
    cod_barras: str
    preco_venda: float
    custo: Optional[float] = None
    vitrine_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
