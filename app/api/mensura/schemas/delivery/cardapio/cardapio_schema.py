# app/schemas/cardapio.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List

class CategoriaMiniSchema(BaseModel):
    slug: str
    slug_pai: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class ProdutoMiniDTO(BaseModel):
    id: int
    descricao: str
    imagem: Optional[str]

    # ✅ usa categoria_id internamente, mas cod_categoria no JSON
    cod_categoria: Optional[int]

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True  # permite usar alias na saída
    )

class ProdutoEmpMiniDTO(BaseModel):
    empresa: int
    cod_barras: str
    preco_venda: float
    subcategoria_id: int
    produto: ProdutoMiniDTO

    model_config = ConfigDict(from_attributes=True)

class VitrineConfigSchema(BaseModel):
    id: int
    cod_empresa: int
    titulo: str
    slug: str
    ordem: int
    cod_categoria: int

    model_config = ConfigDict(from_attributes=True)

class CardapioCategProdutosResponse(BaseModel):
    id: int
    slug: str
    slug_pai: Optional[str]
    descricao: str
    imagem: Optional[str]
    destacar_em_slug: Optional[str]
    href: str
    produtos: List[ProdutoEmpMiniDTO]
    vitrines: Optional[List[VitrineConfigSchema]] = None

    model_config = ConfigDict(from_attributes=True)
