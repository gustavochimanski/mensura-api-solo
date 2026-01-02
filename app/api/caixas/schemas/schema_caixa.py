from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class CaixaStatusEnum(str):
    ABERTO = "ABERTO"
    FECHADO = "FECHADO"

class CaixaBase(BaseModel):
    valor_inicial: Decimal = Field(..., ge=0, description="Valor inicial em dinheiro no caixa")
    observacoes_abertura: Optional[str] = Field(None, max_length=500)

class CaixaCreate(CaixaBase):
    empresa_id: int = Field(..., gt=0, description="ID da empresa")

class CaixaUpdate(BaseModel):
    observacoes_abertura: Optional[str] = Field(None, max_length=500)

class ConferenciaMeioPagamento(BaseModel):
    """Valor conferido para um meio de pagamento específico"""
    meio_pagamento_id: int = Field(..., gt=0, description="ID do meio de pagamento")
    valor_conferido: Decimal = Field(..., ge=0, description="Valor conferido para este meio de pagamento")
    observacoes: Optional[str] = Field(None, max_length=500)

class CaixaFechamentoRequest(BaseModel):
    saldo_real: Decimal = Field(..., ge=0, description="Valor real contado no fechamento (dinheiro físico)")
    observacoes_fechamento: Optional[str] = Field(None, max_length=500)
    conferencias: List[ConferenciaMeioPagamento] = Field(default_factory=list, description="Conferências por tipo de meio de pagamento")

class CaixaResponse(BaseModel):
    id: int
    empresa_id: int
    usuario_id_abertura: int
    usuario_id_fechamento: Optional[int] = None
    valor_inicial: float
    valor_final: Optional[float] = None
    saldo_esperado: Optional[float] = None
    saldo_real: Optional[float] = None
    diferenca: Optional[float] = None
    status: str
    data_abertura: datetime
    data_fechamento: Optional[datetime] = None
    observacoes_abertura: Optional[str] = None
    observacoes_fechamento: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Informações adicionais
    empresa_nome: Optional[str] = None
    usuario_abertura_nome: Optional[str] = None
    usuario_fechamento_nome: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class CaixaResumoResponse(BaseModel):
    """Resumo do caixa para listagem"""
    id: int
    empresa_id: int
    empresa_nome: Optional[str] = None
    usuario_abertura_nome: Optional[str] = None
    valor_inicial: float
    valor_final: Optional[float] = None
    saldo_esperado: Optional[float] = None
    saldo_real: Optional[float] = None
    diferenca: Optional[float] = None
    status: str
    data_abertura: datetime
    data_fechamento: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class ConferenciaMeioPagamentoResponse(BaseModel):
    """Resposta com informações de conferência por meio de pagamento"""
    meio_pagamento_id: int
    meio_pagamento_nome: str
    meio_pagamento_tipo: str
    valor_esperado: float
    valor_conferido: float
    diferenca: float
    quantidade_transacoes: int
    observacoes: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class CaixaConferenciaResumoResponse(BaseModel):
    """Resumo das conferências do caixa por tipo de pagamento"""
    caixa_id: int
    conferencias: List[ConferenciaMeioPagamentoResponse]
    
    model_config = ConfigDict(from_attributes=True)

class CaixaConferenciaEsperadoResponse(BaseModel):
    """Valores esperados por meio de pagamento antes do fechamento"""
    meio_pagamento_id: int
    meio_pagamento_nome: str
    meio_pagamento_tipo: str
    valor_esperado: float
    quantidade_transacoes: int
    
    model_config = ConfigDict(from_attributes=True)

class CaixaValoresEsperadosResponse(BaseModel):
    """Resposta com valores esperados por tipo de pagamento para um caixa aberto"""
    caixa_id: int
    empresa_id: int
    data_abertura: datetime
    valor_inicial_dinheiro: float
    valores_por_meio: List[CaixaConferenciaEsperadoResponse]
    total_esperado_dinheiro: float  # Valor inicial + entradas - saídas
    
    model_config = ConfigDict(from_attributes=True)

# ==================== SCHEMAS DE RETIRADA ====================

class RetiradaTipoEnum(str):
    SANGRIA = "SANGRIA"
    DESPESA = "DESPESA"

class RetiradaCreate(BaseModel):
    tipo: RetiradaTipoEnum = Field(..., description="Tipo de retirada: SANGRIA ou DESPESA")
    valor: Decimal = Field(..., gt=0, description="Valor da retirada")
    observacoes: Optional[str] = Field(None, max_length=500, description="Observações (obrigatório para DESPESA)")

class RetiradaResponse(BaseModel):
    id: int
    caixa_id: int
    tipo: str
    valor: float
    observacoes: Optional[str] = None
    usuario_id: int
    usuario_nome: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

