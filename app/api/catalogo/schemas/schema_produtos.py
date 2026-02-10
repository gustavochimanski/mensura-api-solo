"""
Schemas de Produtos
Centralizado no schema de catalogo
"""
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, Field, condecimal, constr
from app.api.catalogo.schemas.schema_complemento import ComplementoResponse


# ------ Requests de criação/edição ------
class CriarNovoProdutoRequest(BaseModel):
    # ProdutoDeliveryModel
    cod_barras: Optional[constr(min_length=1)] = None  # Opcional - será gerado automaticamente se não fornecido
    descricao: constr(min_length=1, max_length=255)
    imagem: Optional[str] = None
    data_cadastro: Optional[date] = None
    ativo: bool = True
    unidade_medida: Optional[constr(max_length=10)] = None
	    # diretivas removido

    # ProdutoEmpDeliveryModel (já cria o vínculo com a empresa)
    empresa_id: int
    preco_venda: condecimal(max_digits=18, decimal_places=2) = Field(..., ge=0)
    custo: Optional[condecimal(max_digits=18, decimal_places=5)] = None
    sku_empresa: Optional[constr(max_length=60)] = None
    disponivel: bool = True
    exibir_delivery: bool = True

    model_config = ConfigDict(from_attributes=True)


class AtualizarProdutoRequest(BaseModel):
    descricao: Optional[constr(max_length=255)] = None
    imagem: Optional[str] = None
    ativo: Optional[bool] = None
    unidade_medida: Optional[constr(max_length=10)] = None
	    # diretivas removido

    # campos de produto da empresa (opcionais)
    preco_venda: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    custo: Optional[condecimal(max_digits=18, decimal_places=5)] = None
    vitrine_id: Optional[int] = None
    sku_empresa: Optional[constr(max_length=60)] = None
    disponivel: Optional[bool] = None
    exibir_delivery: Optional[bool] = None


# ------ DTOs / Responses ------
class ProdutoBaseDTO(BaseModel):
    cod_barras: str
    descricao: str
    imagem: Optional[str] = None
    cod_categoria: Optional[int] = None   # Categoria do ERP (opcional)
    ativo: bool
    unidade_medida: Optional[str] = None
	    # diretivas removido
    exibir_delivery: bool = True
    tem_receita: bool = False  # Indica se o produto é composto por uma receita (tem itens)

    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProdutoEmpDTO(BaseModel):
    empresa_id: int
    cod_barras: str
    preco_venda: float
    custo: Optional[float] = None
    vitrine_id: Optional[int] = None
    sku_empresa: Optional[str] = None
    disponivel: bool
    exibir_delivery: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CriarNovoProdutoResponse(BaseModel):
    produto: ProdutoBaseDTO
    produto_emp: ProdutoEmpDTO

    model_config = ConfigDict(from_attributes=True)


class ProdutoListItem(BaseModel):
    # Mantido para compatibilidade interna; a listagem pública agora usa `ProdutoListCompact`.
    cod_barras: str
    descricao: str
    imagem: Optional[str] = None
    preco_venda: float
    custo: Optional[float] = None
    cod_categoria: Optional[int] = None    # Categoria do ERP (opcional)
    label_categoria: Optional[str] = None  # Nome da categoria (opcional)
    disponivel: bool
    exibir_delivery: bool = True
    tem_receita: bool = False  # Indica se o produto é composto por uma receita (tem itens)
    adicionais: Optional[List[dict]] = None  # Lista de adicionais (quando produto tiver diretiva CPA)
    model_config = ConfigDict(from_attributes=True)


class ProdutoListCompact(BaseModel):
    id: int
    cod_barras: str
    descricao: str
    imagem: Optional[str] = None
    disponivel: bool
    exibir_delivery: bool = True
    preco_venda: float

    model_config = ConfigDict(from_attributes=True)


class ProdutosPaginadosResponse(BaseModel):
    data: List[ProdutoListCompact]
    total: int
    page: int
    limit: int
    has_more: bool

    model_config = ConfigDict(from_attributes=True)


class ProdutoDetalheResponse(BaseModel):
    produto: ProdutoBaseDTO
    produto_emp: Optional[ProdutoEmpDTO] = None
    complementos: List[ComplementoResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

