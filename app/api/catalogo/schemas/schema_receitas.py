from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, constr, model_validator
from datetime import datetime


class ReceitaIn(BaseModel):
    empresa_id: int
    nome: constr(min_length=1, max_length=100)
    descricao: Optional[str] = None
    preco_venda: Decimal
    imagem: Optional[str] = None
    ativo: bool = True
    disponivel: bool = True


class ReceitaOut(BaseModel):
    id: int
    empresa_id: int
    nome: str
    descricao: Optional[str] = None
    preco_venda: Decimal
    custo_total: Decimal
    imagem: Optional[str] = None
    ativo: bool
    disponivel: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReceitaUpdate(BaseModel):
    nome: Optional[constr(max_length=100)] = None
    descricao: Optional[str] = None
    preco_venda: Optional[Decimal] = None
    imagem: Optional[str] = None
    ativo: Optional[bool] = None
    disponivel: Optional[bool] = None


class ReceitaIngredienteIn(BaseModel):
    """
    Schema para vincular um item a uma receita.
    
    Deve fornecer exatamente um dos seguintes:
    - receita_ingrediente_id: para vincular uma receita como ingrediente
    - produto_cod_barras: para vincular um produto normal
    - combo_id: para vincular um combo
    """
    receita_id: int
    receita_ingrediente_id: Optional[int] = None
    produto_cod_barras: Optional[str] = None
    combo_id: Optional[int] = None
    quantidade: Optional[float] = None
    
    @model_validator(mode='after')
    def validate_exactly_one(self):
        """Valida que exatamente um dos campos seja fornecido"""
        campos_preenchidos = [
            self.receita_ingrediente_id is not None,
            self.produto_cod_barras is not None,
            self.combo_id is not None
        ]
        
        quantidade_preenchidos = sum(campos_preenchidos)
        
        if quantidade_preenchidos == 0:
            raise ValueError("Deve fornecer exatamente um: receita_ingrediente_id, produto_cod_barras ou combo_id")
        if quantidade_preenchidos > 1:
            raise ValueError("Deve fornecer apenas um dos campos: receita_ingrediente_id, produto_cod_barras ou combo_id")
        
        return self


class ReceitaIngredienteOut(BaseModel):
    """Schema de resposta para item de receita (pode ser sub-receita, produto ou combo)"""
    id: int
    receita_id: int
    receita_ingrediente_id: Optional[int] = None
    produto_cod_barras: Optional[str] = None
    combo_id: Optional[int] = None
    quantidade: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)


class ReceitaIngredienteDetalhadoOut(BaseModel):
    """
    Schema de resposta para item de receita com dados detalhados.
    Pode representar sub-receita, produto ou combo.
    """
    id: int
    receita_id: int
    receita_ingrediente_id: Optional[int] = None
    produto_cod_barras: Optional[str] = None
    combo_id: Optional[int] = None
    quantidade: Optional[float] = None
    
    # Dados da sub-receita (se receita_ingrediente_id estiver preenchido)
    receita_ingrediente_nome: Optional[str] = None
    receita_ingrediente_descricao: Optional[str] = None
    receita_ingrediente_preco_venda: Optional[Decimal] = None
    
    # Dados do produto (se produto_cod_barras estiver preenchido)
    produto_descricao: Optional[str] = None
    produto_imagem: Optional[str] = None
    
    # Dados do combo (se combo_id estiver preenchido)
    combo_titulo: Optional[str] = None
    combo_descricao: Optional[str] = None
    combo_preco_total: Optional[Decimal] = None
    
    model_config = ConfigDict(from_attributes=True)


class ReceitaComIngredientesOut(BaseModel):
    """Schema de resposta para receita com seus itens incluídos"""
    id: int
    empresa_id: int
    nome: str
    descricao: Optional[str] = None
    preco_venda: Decimal
    custo_total: Decimal
    imagem: Optional[str] = None
    ativo: bool
    disponivel: bool
    created_at: datetime
    updated_at: datetime
    ingredientes: list[ReceitaIngredienteDetalhadoOut] = []
    model_config = ConfigDict(from_attributes=True)


class AdicionalIn(BaseModel):
    receita_id: int
    adicional_id: int


class AdicionalOut(BaseModel):
    id: int
    receita_id: int
    adicional_id: int
    preco: Optional[Decimal] = None
    model_config = ConfigDict(from_attributes=True)


class ClonarIngredientesRequest(BaseModel):
    """Schema para clonar ingredientes de uma receita para outra"""
    receita_origem_id: int
    receita_destino_id: int


class ClonarIngredientesResponse(BaseModel):
    """Schema de resposta para clonagem de ingredientes"""
    receita_origem_id: int
    receita_destino_id: int
    ingredientes_clonados: int
    mensagem: str

