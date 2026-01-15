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
    Schema para vincular um ingrediente ou sub-receita a uma receita.
    
    Deve fornecer exatamente um dos seguintes:
    - ingrediente_id: para vincular um ingrediente básico
    - receita_ingrediente_id: para vincular uma receita como ingrediente
    """
    receita_id: int
    ingrediente_id: Optional[int] = None
    receita_ingrediente_id: Optional[int] = None
    quantidade: Optional[float] = None
    
    @model_validator(mode='after')
    def validate_exactly_one(self):
        """Valida que exatamente um dos campos (ingrediente_id ou receita_ingrediente_id) seja fornecido"""
        has_ingrediente = self.ingrediente_id is not None
        has_receita = self.receita_ingrediente_id is not None
        
        if not (has_ingrediente or has_receita):
            raise ValueError("Deve fornecer ingrediente_id ou receita_ingrediente_id")
        if has_ingrediente and has_receita:
            raise ValueError("Deve fornecer apenas um: ingrediente_id ou receita_ingrediente_id")
        
        return self


class ReceitaIngredienteOut(BaseModel):
    """Schema de resposta para ingrediente de receita (pode ser ingrediente básico ou sub-receita)"""
    id: int
    receita_id: int
    ingrediente_id: Optional[int] = None
    receita_ingrediente_id: Optional[int] = None
    quantidade: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)


class ReceitaIngredienteDetalhadoOut(BaseModel):
    """
    Schema de resposta para ingrediente de receita com dados detalhados.
    Pode representar um ingrediente básico ou uma sub-receita.
    """
    id: int
    receita_id: int
    ingrediente_id: Optional[int] = None
    receita_ingrediente_id: Optional[int] = None
    quantidade: Optional[float] = None
    
    # Dados do ingrediente básico (se ingrediente_id estiver preenchido)
    ingrediente_nome: Optional[str] = None
    ingrediente_descricao: Optional[str] = None
    ingrediente_unidade_medida: Optional[str] = None
    ingrediente_custo: Optional[Decimal] = None
    
    # Dados da sub-receita (se receita_ingrediente_id estiver preenchido)
    receita_ingrediente_nome: Optional[str] = None
    receita_ingrediente_descricao: Optional[str] = None
    receita_ingrediente_preco_venda: Optional[Decimal] = None
    
    model_config = ConfigDict(from_attributes=True)


class ReceitaComIngredientesOut(BaseModel):
    """Schema de resposta para receita com seus ingredientes incluídos"""
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

