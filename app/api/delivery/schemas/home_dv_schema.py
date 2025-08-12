from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class CategoriaMiniSchema(BaseModel):
    id: int
    slug: str
    parent_id: Optional[int] = None
    descricao: str
    posicao: int
    imagem: Optional[str] = None
    label: str
    href: str
    slug_pai: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ProdutoMiniDTO(BaseModel):
    cod_barras: str
    descricao: str
    imagem: Optional[str] = None
    cod_categoria: Optional[int] = None
    ativo: bool = True
    unidade_medida: Optional[str] = None
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class ProdutoEmpMiniDTO(BaseModel):
    empresa_id: int
    cod_barras: str
    preco_venda: float
    vitrine_id: Optional[int] = None
    disponivel: bool = True
    produto: ProdutoMiniDTO
    model_config = ConfigDict(from_attributes=True)

class VitrineConfigSchema(BaseModel):
    id: int
    cod_categoria: int  # FK -> categoria.id
    titulo: str
    slug: str
    ordem: int
    is_home: bool
    model_config = ConfigDict(from_attributes=True)

class VitrineComProdutosResponse(BaseModel):
    id: int
    titulo: str
    slug: str
    ordem: int
    produtos: List[ProdutoEmpMiniDTO]
    is_home: bool
    model_config = ConfigDict(from_attributes=True)

class HomeResponse(BaseModel):
    categorias: List[CategoriaMiniSchema]
    vitrines: List[VitrineComProdutosResponse]
    model_config = ConfigDict(from_attributes=True)
