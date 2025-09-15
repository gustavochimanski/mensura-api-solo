"""
Schemas específicos para comunicação com Printer API
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime


class ItemPedidoPrinter(BaseModel):
    """Item de pedido formatado para impressão"""
    descricao: str = Field(..., description="Descrição do produto")
    quantidade: int = Field(..., ge=1, description="Quantidade do item")
    preco: float = Field(..., ge=0, description="Preço unitário do item")
    observacao: Optional[str] = Field(None, description="Observação específica do item")


class PedidoPrinterRequest(BaseModel):
    """Pedido formatado para envio à Printer API"""
    numero: int = Field(..., ge=1, description="Número do pedido")
    cliente: str = Field(..., min_length=1, description="Nome do cliente")
    telefone_cliente: Optional[str] = Field(None, description="Telefone do cliente")
    itens: List[ItemPedidoPrinter] = Field(..., min_items=1, description="Lista de itens do pedido")
    subtotal: float = Field(..., ge=0, description="Subtotal do pedido")
    desconto: float = Field(0, ge=0, description="Valor do desconto")
    taxa_entrega: float = Field(0, ge=0, description="Taxa de entrega")
    taxa_servico: float = Field(0, ge=0, description="Taxa de serviço")
    total: float = Field(..., ge=0, description="Total do pedido")
    tipo_pagamento: str = Field(..., min_length=1, description="Tipo de pagamento")
    troco: Optional[float] = Field(None, ge=0, description="Valor do troco")
    observacao_geral: Optional[str] = Field(None, description="Observação geral do pedido")
    endereco: Optional[str] = Field(None, description="Endereço de entrega")
    data_criacao: datetime = Field(..., description="Data de criação do pedido")
    
    @validator('troco')
    def validar_troco_dinheiro(cls, v, values):
        tipo_pagamento = values.get('tipo_pagamento', '').upper()
        if tipo_pagamento == 'DINHEIRO' and v is None:
            raise ValueError('Troco é obrigatório quando o tipo de pagamento é DINHEIRO')
        return v


class ConfigImpressaoPrinter(BaseModel):
    """Configurações de impressão para Printer API"""
    nome_impressora: Optional[str] = Field(None, description="Nome da impressora")
    fonte_nome: str = Field("Courier New", description="Nome da fonte")
    fonte_tamanho: int = Field(24, ge=8, le=72, description="Tamanho da fonte")
    espacamento_linha: int = Field(40, ge=10, le=80, description="Espaçamento entre linhas")
    espacamento_item: int = Field(50, ge=20, le=120, description="Espaçamento entre itens")
    nome_estabelecimento: str = Field("RESTAURANTE MENSURA", description="Nome do estabelecimento")
    mensagem_rodape: str = Field("Obrigado pela preferência!", description="Mensagem do rodapé")
    formato_preco: str = Field("R$ {:.2f}", description="Formato do preço")
    formato_total: str = Field("TOTAL: R$ {:.2f}", description="Formato do total")


class ImpressaoPedidoRequest(BaseModel):
    """Request para impressão de pedido"""
    pedido: PedidoPrinterRequest = Field(..., description="Dados do pedido")
    config: Optional[ConfigImpressaoPrinter] = Field(None, description="Configurações de impressão")


class RespostaImpressaoPrinter(BaseModel):
    """Resposta da operação de impressão da Printer API"""
    sucesso: bool = Field(..., description="Se a impressão foi bem-sucedida")
    mensagem: str = Field(..., description="Mensagem de resultado")
    numero_pedido: Optional[int] = Field(None, description="Número do pedido impresso")
    timestamp: Optional[datetime] = Field(None, description="Timestamp da impressão")


class StatusPrinterResponse(BaseModel):
    """Status da Printer API"""
    conectado: bool = Field(..., description="Se a Printer API está conectada")
    mensagem: str = Field(..., description="Mensagem de status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp da verificação")


class ImpressaoMultiplaRequest(BaseModel):
    """Request para impressão múltipla de pedidos"""
    empresa_id: int = Field(..., ge=1, description="ID da empresa")
    limite: int = Field(10, ge=1, le=50, description="Número máximo de pedidos para imprimir")
    config: Optional[ConfigImpressaoPrinter] = Field(None, description="Configurações de impressão")


class RespostaImpressaoMultipla(BaseModel):
    """Resposta da operação de impressão múltipla"""
    sucesso: bool = Field(..., description="Se todas as impressões foram bem-sucedidas")
    mensagem: str = Field(..., description="Mensagem de resultado")
    pedidos_impressos: int = Field(0, ge=0, description="Número de pedidos impressos com sucesso")
    pedidos_falharam: int = Field(0, ge=0, description="Número de pedidos que falharam")
    detalhes: List[RespostaImpressaoPrinter] = Field(default_factory=list, description="Detalhes de cada impressão")


class PedidoParaImpressao(BaseModel):
    """Pedido formatado para impressão com dados completos"""
    id: int = Field(..., description="ID do pedido")
    status: str = Field(..., description="Status do pedido")
    cliente_nome: str = Field(..., description="Nome do cliente")
    cliente_telefone: Optional[str] = Field(None, description="Telefone do cliente")
    valor_total: float = Field(..., description="Valor total do pedido")
    data_criacao: datetime = Field(..., description="Data de criação")
    endereco_cliente: Optional[str] = Field(None, description="Endereço do cliente")
    meio_pagamento_descricao: Optional[str] = Field(None, description="Descrição do meio de pagamento")
    observacao_geral: Optional[str] = Field(None, description="Observação geral")
    itens: List[ItemPedidoPrinter] = Field(..., description="Itens do pedido")
    desconto: float = Field(0, description="Valor do desconto")
    taxa_entrega: float = Field(0, description="Taxa de entrega")
    taxa_servico: float = Field(0, description="Taxa de serviço")
    troco_para: Optional[float] = Field(None, description="Valor do troco para")


class PedidoPendenteImpressaoResponse(BaseModel):
    """Resposta formatada para pedidos pendentes de impressão"""
    numero: int = Field(..., description="Número do pedido")
    cliente: str = Field(..., description="Nome do cliente")
    telefone_cliente: Optional[str] = Field(None, description="Telefone do cliente")
    itens: List[ItemPedidoPrinter] = Field(..., description="Lista de itens do pedido")
    desconto: float = Field(0, description="Valor do desconto")
    taxa_entrega: float = Field(0, description="Taxa de entrega")
    taxa_servico: float = Field(0, description="Taxa de serviço")
    total: float = Field(..., description="Valor total do pedido")
    tipo_pagamento: str = Field(..., description="Tipo de pagamento")
    troco: Optional[float] = Field(None, description="Valor do troco")
    observacao_geral: Optional[str] = Field(None, description="Observação geral do pedido")
    endereco: Optional[str] = Field(None, description="Endereço de entrega")
    data_criacao: datetime = Field(..., description="Data de criação do pedido")