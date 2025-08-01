# app/schemas/cardapio.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class CategoriaMiniSchema(BaseModel):
    slug: str
    parent_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class ProdutoMiniDTO(BaseModel):
    cod_barras: str
    descricao: str
    imagem: Optional[str] = None
    cod_categoria: Optional[int] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

class ProdutoEmpMiniDTO(BaseModel):
    empresa_id: int
    cod_barras: str
    preco_venda: float
    vitrine_id: int
    produto: ProdutoMiniDTO

    model_config = ConfigDict(from_attributes=True)

class VitrineConfigSchema(BaseModel):
    id: int
    cod_categoria: int
    titulo: str
    slug: str
    ordem: int

    model_config = ConfigDict(from_attributes=True)

class VitrineComProdutosResponse(BaseModel):
    id: int
    titulo: str
    slug: str
    ordem: int
    produtos: List[ProdutoEmpMiniDTO]

    model_config = ConfigDict(from_attributes=True)
