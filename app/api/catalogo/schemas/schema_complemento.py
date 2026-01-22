from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, condecimal, model_validator


# ------ Requests ------
class CriarComplementoRequest(BaseModel):
    """Request para criar um complemento.
    
    NOTA: obrigatorio, quantitativo, minimo_itens e maximo_itens não são mais
    definidos aqui. Essas configurações são definidas na vinculação do complemento
    a produtos, receitas ou combos.
    """
    empresa_id: int
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    ordem: int = 0

    model_config = ConfigDict(from_attributes=True)


class AtualizarComplementoRequest(BaseModel):
    """Request para atualizar um complemento.
    
    NOTA: obrigatorio, quantitativo, minimo_itens e maximo_itens não podem mais
    ser atualizados aqui. Essas configurações são atualizadas na vinculação
    do complemento a produtos, receitas ou combos.
    """
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    ativo: Optional[bool] = None
    ordem: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class CriarItemRequest(BaseModel):
    """Request para criar um item de complemento (independente)"""
    empresa_id: int
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    imagem: Optional[str] = Field(None, max_length=255, description="URL pública da imagem do adicional (opcional)")
    preco: condecimal(max_digits=18, decimal_places=2) = Field(default=0)
    custo: condecimal(max_digits=18, decimal_places=2) = Field(default=0)
    ativo: bool = True

    model_config = ConfigDict(from_attributes=True)


class CriarAdicionalRequest(BaseModel):
    """Request para criar um adicional dentro de um complemento (DEPRECADO - usar CriarItemRequest)"""
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    preco: condecimal(max_digits=18, decimal_places=2) = Field(default=0)
    custo: condecimal(max_digits=18, decimal_places=2) = Field(default=0)
    ativo: bool = True
    ordem: int = 0

    model_config = ConfigDict(from_attributes=True)


class AtualizarAdicionalRequest(BaseModel):
    """Request para atualizar um adicional (item) genérico.

    Atenção: para atualizar apenas o preço dentro de um complemento específico,
    use o endpoint dedicado de preço por complemento.
    """
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    imagem: Optional[str] = Field(None, max_length=255, description="URL pública da imagem do adicional (opcional)")
    preco: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    custo: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    ativo: Optional[bool] = None
    ordem: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class AtualizarPrecoItemComplementoRequest(BaseModel):
    """Request para atualizar o preço de um item dentro de um complemento específico."""
    preco: condecimal(max_digits=18, decimal_places=2)


# ------ Responses ------
class AdicionalResponse(BaseModel):
    """Response para adicional dentro de um complemento.

    Observação: o campo `preco` representa o preço **efetivo no contexto do complemento**.
    Se existir um preço específico por complemento, ele será retornado aqui; caso contrário,
    será o preço padrão do adicional.
    """
    id: int
    nome: str
    descricao: Optional[str] = None
    imagem: Optional[str] = None
    preco: float
    custo: float
    ativo: bool
    ordem: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplementoResponse(BaseModel):
    """Response para complemento com seus adicionais.
    
    NOTA: Quando retornado de uma vinculação (produto/receita/combo),
    os campos obrigatorio, quantitativo, minimo_itens, maximo_itens e ordem
    vêm da vinculação, não do complemento em si.
    
    Quando retornado do CRUD direto (sem vinculação), esses campos não existem.
    """
    id: int
    empresa_id: int
    nome: str
    descricao: Optional[str] = None
    obrigatorio: Optional[bool] = None  # Da vinculação (None quando não vinculado)
    quantitativo: Optional[bool] = None  # Da vinculação (None quando não vinculado)
    minimo_itens: Optional[int] = Field(
        None,
        description="Mínimo de itens da vinculação (None quando não vinculado ou sem mínimo).",
    )
    maximo_itens: Optional[int] = Field(
        None,
        description="Máximo de itens da vinculação (None quando não vinculado ou sem limite).",
    )
    ordem: int  # Da vinculação ou do complemento
    ativo: bool
    adicionais: List[AdicionalResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplementoResumidoResponse(BaseModel):
    """Versão simplificada para uso em listagens.
    
    Todos os campos de configuração vêm da vinculação.
    """
    id: int
    nome: str
    obrigatorio: bool  # Da vinculação
    quantitativo: bool  # Da vinculação
    minimo_itens: Optional[int] = None  # Da vinculação
    maximo_itens: Optional[int] = None  # Da vinculação
    ordem: int  # Da vinculação

    model_config = ConfigDict(from_attributes=True)


# ------ Configuração de vinculação de complemento ------
class ConfiguracaoVinculacaoComplemento(BaseModel):
    """Configurações específicas de um complemento na vinculação.
    
    Todas as configurações são obrigatórias na vinculação.
    
    IMPORTANTE: Se quantitativo for False, minimo_itens e maximo_itens são automaticamente definidos como None.
    """
    complemento_id: int = Field(..., description="ID do complemento a vincular")
    ordem: Optional[int] = Field(None, description="Ordem do complemento (opcional, usa índice se não informado)")
    obrigatorio: bool = Field(..., description="Se o complemento é obrigatório nesta vinculação")
    quantitativo: bool = Field(..., description="Se permite quantidade (ex: 2x bacon) e múltipla escolha nesta vinculação")
    minimo_itens: Optional[int] = Field(None, ge=0, description="Quantidade mínima de itens nesta vinculação (None = sem mínimo)")
    maximo_itens: Optional[int] = Field(None, ge=0, description="Quantidade máxima de itens nesta vinculação (None = sem limite)")
    
    @model_validator(mode='after')
    def validate_quantitativo(self):
        """Se quantitativo for False, define minimo_itens e maximo_itens como None."""
        if not self.quantitativo:
            self.minimo_itens = None
            self.maximo_itens = None
        return self


# ------ Vincular complementos a produtos ------
class VincularComplementosProdutoRequest(BaseModel):
    """Request para vincular múltiplos complementos a um produto
    
    Aceita dois formatos:
    1. Formato simples: complemento_ids + ordens (mantém compatibilidade)
    2. Formato completo: configuracoes (permite definir obrigatorio, minimo_itens, maximo_itens por complemento)
    """
    # Formato simples (compatibilidade)
    complemento_ids: Optional[List[int]] = Field(None, description="IDs dos complementos a vincular (formato simples)")
    ordens: Optional[List[int]] = Field(None, description="Ordem de cada complemento (opcional, usa índice se não informado)")
    
    # Formato completo (novo)
    configuracoes: Optional[List[ConfiguracaoVinculacaoComplemento]] = Field(
        None, 
        description="Configurações detalhadas por complemento (formato completo). Se fornecido, ignora complemento_ids e ordens."
    )
    
    @model_validator(mode='after')
    def validate_at_least_one_format(self):
        if not self.configuracoes and not self.complemento_ids:
            raise ValueError("Deve fornecer 'complemento_ids' ou 'configuracoes'")
        return self


class VincularComplementosProdutoResponse(BaseModel):
    """Response após vincular complementos"""
    produto_cod_barras: str
    complementos_vinculados: List[ComplementoResumidoResponse]
    message: str = "Complementos vinculados com sucesso"

    model_config = ConfigDict(from_attributes=True)


# ------ Vincular complementos a receitas ------
class VincularComplementosReceitaRequest(BaseModel):
    """Request para vincular múltiplos complementos a uma receita
    
    Aceita dois formatos:
    1. Formato simples: complemento_ids + ordens (mantém compatibilidade)
    2. Formato completo: configuracoes (permite definir obrigatorio, minimo_itens, maximo_itens por complemento)
    
    Nota: Listas vazias são permitidas para remover todas as vinculações.
    """
    # Formato simples (compatibilidade)
    complemento_ids: Optional[List[int]] = Field(None, description="IDs dos complementos a vincular (formato simples). Lista vazia remove todas as vinculações.")
    ordens: Optional[List[int]] = Field(None, description="Ordem de cada complemento (opcional, usa índice se não informado)")
    
    # Formato completo (novo)
    configuracoes: Optional[List[ConfiguracaoVinculacaoComplemento]] = Field(
        None, 
        description="Configurações detalhadas por complemento (formato completo). Se fornecido, ignora complemento_ids e ordens. Lista vazia remove todas as vinculações."
    )
    
    @model_validator(mode='after')
    def validate_at_least_one_format(self):
        # Listas vazias são permitidas (remove todas as vinculações)
        if self.complemento_ids is not None and len(self.complemento_ids) == 0:
            return self
        if self.configuracoes is not None and len(self.configuracoes) == 0:
            return self
        # Verifica se pelo menos um formato foi fornecido (e não vazio)
        if not self.configuracoes and (not self.complemento_ids or len(self.complemento_ids) == 0):
            raise ValueError("Deve fornecer 'complemento_ids' (não vazio) ou 'configuracoes' (não vazio)")
        return self


class VincularComplementosReceitaResponse(BaseModel):
    """Response após vincular complementos a uma receita"""
    receita_id: int
    complementos_vinculados: List[ComplementoResumidoResponse]
    message: str = "Complementos vinculados com sucesso"

    model_config = ConfigDict(from_attributes=True)


# ------ Vincular complementos a combos ------
class VincularComplementosComboRequest(BaseModel):
    """Request para vincular múltiplos complementos a um combo
    
    Aceita dois formatos:
    1. Formato simples: complemento_ids + ordens (mantém compatibilidade)
    2. Formato completo: configuracoes (permite definir obrigatorio, minimo_itens, maximo_itens por complemento)
    
    Nota: Para combos, complemento_ids pode ser uma lista vazia para remover todas as vinculações.
    """
    # Formato simples (compatibilidade)
    complemento_ids: Optional[List[int]] = Field(None, description="IDs dos complementos a vincular (formato simples). Lista vazia remove todas as vinculações.")
    ordens: Optional[List[int]] = Field(None, description="Ordem de cada complemento (opcional, usa índice se não informado)")
    
    # Formato completo (novo)
    configuracoes: Optional[List[ConfiguracaoVinculacaoComplemento]] = Field(
        None, 
        description="Configurações detalhadas por complemento (formato completo). Se fornecido, ignora complemento_ids e ordens."
    )
    
    @model_validator(mode='after')
    def validate_at_least_one_format(self):
        # Para combos, lista vazia é permitida (remove todas as vinculações)
        if self.complemento_ids is not None and len(self.complemento_ids) == 0:
            return self
        if not self.configuracoes and (not self.complemento_ids or len(self.complemento_ids) == 0):
            raise ValueError("Deve fornecer 'complemento_ids' (não vazio) ou 'configuracoes'")
        return self


class VincularComplementosComboResponse(BaseModel):
    """Response após vincular complementos a um combo"""
    combo_id: int
    complementos_vinculados: List[ComplementoResumidoResponse]
    message: str = "Complementos vinculados com sucesso"

    model_config = ConfigDict(from_attributes=True)


# ------ Vincular itens a complementos (N:N) ------
class VincularItensComplementoRequest(BaseModel):
    """Request para vincular múltiplos itens a um complemento"""
    item_ids: List[int] = Field(..., description="IDs dos itens a vincular")
    ordens: Optional[List[int]] = Field(None, description="Ordem de cada item (opcional, usa índice se não informado)")
    precos: Optional[List[condecimal(max_digits=18, decimal_places=2)]] = Field(
        None,
        description=(
            "Preços específicos por item neste complemento (alinhados por índice com item_ids). "
            "Se não informado ou posição nula, usa o preço padrão do item."
        ),
    )


class VincularItensComplementoResponse(BaseModel):
    """Response após vincular itens a um complemento"""
    complemento_id: int
    itens_vinculados: List[AdicionalResponse]
    message: str = "Itens vinculados com sucesso"

    model_config = ConfigDict(from_attributes=True)


class VincularItemComplementoRequest(BaseModel):
    """Request para vincular um único item adicional a um complemento"""
    item_id: int = Field(..., description="ID do item adicional a vincular")
    ordem: Optional[int] = Field(None, description="Ordem do item no complemento (opcional)")
    preco_complemento: Optional[condecimal(max_digits=18, decimal_places=2)] = Field(
        None, 
        description="Preço específico do item neste complemento (opcional, sobrescreve o preço padrão)"
    )

    model_config = ConfigDict(from_attributes=True)


class VincularItemComplementoResponse(BaseModel):
    """Response após vincular um item adicional a um complemento"""
    complemento_id: int
    item_vinculado: AdicionalResponse
    message: str = "Item vinculado com sucesso"

    model_config = ConfigDict(from_attributes=True)


class ItemOrdemRequest(BaseModel):
    """Item com ordem para atualização"""
    item_id: int
    ordem: int


class AtualizarOrdemItensRequest(BaseModel):
    """Request para atualizar a ordem dos itens em um complemento
    
    Aceita dois formatos:
    1. item_ids: Lista de IDs na ordem desejada (ordem = índice) - Formato simples
    2. item_ordens: Lista de objetos com item_id e ordem explícita - Formato completo
    """
    item_ids: Optional[List[int]] = Field(None, description="IDs dos itens na ordem desejada (ordem = índice)")
    item_ordens: Optional[List[ItemOrdemRequest]] = Field(None, description="Lista de itens com suas ordens explícitas")
    
    model_config = ConfigDict(from_attributes=True)

