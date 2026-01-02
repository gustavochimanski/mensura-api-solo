from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum

class CaixaAberturaStatusEnum(str, Enum):
    ABERTO = "ABERTO"
    FECHADO = "FECHADO"

class CaixaAberturaBase(BaseModel):
    """Schema base para abertura de caixa"""
    valor_inicial: Decimal = Field(..., ge=0, description="Valor inicial em dinheiro no caixa")
    data_hora_abertura: Optional[datetime] = Field(None, description="Data e hora da abertura (opcional, usa timestamp atual se não informado)")
    observacoes_abertura: Optional[str] = Field(None, max_length=500)

class CaixaAberturaCreate(CaixaAberturaBase):
    """Schema para criar uma nova abertura de caixa"""
    caixa_id: int = Field(..., gt=0, description="ID do caixa cadastrado")
    empresa_id: int = Field(..., gt=0, description="ID da empresa")

class CaixaAberturaUpdate(BaseModel):
    """Schema para atualizar uma abertura de caixa (apenas observações)"""
    observacoes_abertura: Optional[str] = Field(None, max_length=500)

class ConferenciaMeioPagamento(BaseModel):
    """Valor conferido para um meio de pagamento específico"""
    meio_pagamento_id: int = Field(..., gt=0, description="ID do meio de pagamento")
    valor_conferido: Decimal = Field(..., ge=0, description="Valor conferido para este meio de pagamento")
    observacoes: Optional[str] = Field(None, max_length=500)

class CaixaAberturaFechamentoRequest(BaseModel):
    """Schema para fechar uma abertura de caixa"""
    saldo_real: Decimal = Field(..., ge=0, description="Valor real contado no fechamento (dinheiro físico)")
    data_hora_fechamento: Optional[datetime] = Field(None, description="Data e hora do fechamento (opcional, usa timestamp atual se não informado)")
    observacoes_fechamento: Optional[str] = Field(None, max_length=500)
    conferencias: List[ConferenciaMeioPagamento] = Field(default_factory=list, description="Conferências por tipo de meio de pagamento")

class CaixaAberturaResponse(BaseModel):
    """Schema de resposta para abertura de caixa"""
    id: int
    caixa_id: int
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
    data_hora_abertura: Optional[datetime] = None
    data_hora_fechamento: Optional[datetime] = None
    observacoes_abertura: Optional[str] = None
    observacoes_fechamento: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Informações adicionais
    caixa_nome: Optional[str] = None
    empresa_nome: Optional[str] = None
    usuario_abertura_nome: Optional[str] = None
    usuario_fechamento_nome: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class CaixaAberturaResumoResponse(BaseModel):
    """Resumo da abertura de caixa para listagem"""
    id: int
    caixa_id: int
    caixa_nome: Optional[str] = None
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
    data_hora_abertura: Optional[datetime] = None
    data_hora_fechamento: Optional[datetime] = None
    
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

class CaixaAberturaConferenciaResumoResponse(BaseModel):
    """Resumo das conferências da abertura de caixa por tipo de pagamento"""
    caixa_abertura_id: int
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

class CaixaAberturaValoresEsperadosResponse(BaseModel):
    """Resposta com valores esperados por tipo de pagamento para uma abertura de caixa aberta"""
    caixa_abertura_id: int
    caixa_id: int
    empresa_id: int
    data_abertura: datetime
    valor_inicial_dinheiro: float
    valores_por_meio: List[CaixaConferenciaEsperadoResponse]
    total_esperado_dinheiro: float  # Valor inicial + entradas - saídas
    
    model_config = ConfigDict(from_attributes=True)

# ==================== SCHEMAS DE RETIRADA ====================

class RetiradaTipoEnum(str, Enum):
    SANGRIA = "SANGRIA"
    DESPESA = "DESPESA"

class RetiradaCreate(BaseModel):
    tipo: RetiradaTipoEnum = Field(..., description="Tipo de retirada: SANGRIA ou DESPESA")
    valor: Decimal = Field(..., gt=0, description="Valor da retirada")
    observacoes: Optional[str] = Field(None, max_length=500, description="Observações (obrigatório para DESPESA)")

class RetiradaResponse(BaseModel):
    id: int
    empresa_id: int
    caixa_abertura_id: int
    tipo: str
    valor: float
    observacoes: Optional[str] = None
    usuario_id: int
    usuario_nome: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

