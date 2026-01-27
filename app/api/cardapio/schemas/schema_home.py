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
    adicionais: Optional[List[dict]] = None  # Lista de adicionais (quando produto tiver diretiva CPA)
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
    cod_categoria: Optional[int] = None  # FK -> categoria.id (opcional)
    titulo: str
    slug: str
    ordem: int
    is_home: bool
    model_config = ConfigDict(from_attributes=True)

class ComboMiniDTO(BaseModel):
    id: int
    empresa_id: int
    titulo: str
    descricao: str
    preco_total: float
    imagem: Optional[str] = None
    ativo: bool
    vitrine_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class ReceitaMiniDTO(BaseModel):
    id: int
    empresa_id: int
    nome: str
    descricao: Optional[str] = None
    preco_venda: float
    imagem: Optional[str] = None
    vitrine_id: Optional[int] = None
    disponivel: bool = True
    ativo: bool = True
    model_config = ConfigDict(from_attributes=True)

class VitrineComProdutosResponse(BaseModel):
    id: int
    titulo: str
    slug: str
    ordem: int
    produtos: List[ProdutoEmpMiniDTO]
    combos: Optional[List[ComboMiniDTO]] = None
    receitas: Optional[List[ReceitaMiniDTO]] = None
    is_home: bool
    cod_categoria: Optional[int] = None
    href_categoria: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class HomeResponse(BaseModel):
    categorias: List[CategoriaMiniSchema]
    vitrines: List[VitrineComProdutosResponse]
    model_config = ConfigDict(from_attributes=True)


class LandingPageStoreResponse(BaseModel):
    """
    Resposta para montar a landing page da store (sem categorias).
    """
    vitrines: List[VitrineComProdutosResponse]
    model_config = ConfigDict(from_attributes=True)

class CategoryPageResponse(BaseModel):
    categoria: CategoriaMiniSchema
    subcategorias: List[CategoriaMiniSchema]
    vitrines: List[VitrineComProdutosResponse]
    vitrines_filho: List[VitrineComProdutosResponse]
    model_config = ConfigDict(from_attributes=True)
