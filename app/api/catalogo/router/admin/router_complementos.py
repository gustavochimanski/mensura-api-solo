from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session

from app.api.catalogo.schemas.schema_complemento import (
    ComplementoResponse,
    CriarComplementoRequest,
    AtualizarComplementoRequest,
    AdicionalResponse,
    VincularComplementosProdutoRequest,
    VincularComplementosProdutoResponse,
    VincularComplementosReceitaRequest,
    VincularComplementosReceitaResponse,
    VincularComplementosComboRequest,
    VincularComplementosComboResponse,
    VincularItensComplementoRequest,
    VincularItensComplementoResponse,
    VincularItemComplementoRequest,
    VincularItemComplementoResponse,
    AtualizarOrdemItensRequest,
    AtualizarPrecoItemComplementoRequest,
)
from app.api.catalogo.services.service_complemento import ComplementoService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/catalogo/admin/complementos",
    tags=["Admin - Catalogo - Complementos"],
    dependencies=[Depends(get_current_user)]
)


# ------ Complementos ------
@router.get("/", response_model=List[ComplementoResponse])
def listar_complementos(
    empresa_id: int,
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
):
    """Lista todos os complementos de uma empresa."""
    logger.info(f"[Complementos] Listar - empresa={empresa_id} apenas_ativos={apenas_ativos}")
    service = ComplementoService(db)
    return service.listar_complementos(empresa_id, apenas_ativos)


@router.post("/", response_model=ComplementoResponse, status_code=status.HTTP_201_CREATED)
def criar_complemento(
    req: CriarComplementoRequest,
    db: Session = Depends(get_db),
):
    """
    Cria um novo complemento.
    
    Um complemento é um grupo de itens adicionais que podem ser vinculados a produtos.
    Permite configurar quantidade mínima e máxima de itens que o cliente pode escolher.
    
    **Parâmetros importantes:**
    - `minimo_itens`: Quantidade mínima de itens que o cliente deve escolher (None = sem mínimo)
    - `maximo_itens`: Quantidade máxima de itens que o cliente pode escolher (None = sem limite)
    - `obrigatorio`: Se o complemento é obrigatório para o produto
    - `quantitativo`: Se permite quantidade (ex: 2x bacon) e múltipla escolha
    """
    logger.info(f"[Complementos] Criar - empresa={req.empresa_id} nome={req.nome}")
    service = ComplementoService(db)
    return service.criar_complemento(req)


@router.get("/{complemento_id}", response_model=ComplementoResponse)
def buscar_complemento(
    complemento_id: int,
    db: Session = Depends(get_db),
):
    """Busca um complemento por ID."""
    logger.info(f"[Complementos] Buscar - id={complemento_id}")
    service = ComplementoService(db)
    return service.buscar_por_id(complemento_id)


@router.put("/{complemento_id}", response_model=ComplementoResponse)
def atualizar_complemento(
    complemento_id: int,
    req: AtualizarComplementoRequest,
    db: Session = Depends(get_db),
):
    """
    Atualiza um complemento existente.
    
    Permite atualizar as configurações do complemento, incluindo:
    - `minimo_itens`: Quantidade mínima de itens que o cliente deve escolher
    - `maximo_itens`: Quantidade máxima de itens que o cliente pode escolher
    - `obrigatorio`: Se o complemento é obrigatório
    - `quantitativo`: Se permite quantidade e múltipla escolha
    - `ativo`: Status ativo/inativo
    
    Todos os campos são opcionais (apenas os fornecidos serão atualizados).
    """
    logger.info(f"[Complementos] Atualizar - id={complemento_id}")
    service = ComplementoService(db)
    return service.atualizar_complemento(complemento_id, req)


@router.delete("/{complemento_id}", status_code=status.HTTP_200_OK)
def deletar_complemento(
    complemento_id: int,
    db: Session = Depends(get_db),
):
    """Deleta um complemento."""
    logger.info(f"[Complementos] Deletar - id={complemento_id}")
    service = ComplementoService(db)
    service.deletar_complemento(complemento_id)
    return {"message": "Complemento deletado com sucesso"}


@router.post("/produto/{cod_barras}/vincular", response_model=VincularComplementosProdutoResponse, status_code=status.HTTP_200_OK)
def vincular_complementos_produto(
    cod_barras: str,
    req: VincularComplementosProdutoRequest,
    db: Session = Depends(get_db),
):
    """Vincula múltiplos complementos a um produto."""
    logger.info(f"[Complementos] Vincular - produto={cod_barras} complementos={req.complemento_ids}")
    service = ComplementoService(db)
    return service.vincular_complementos_produto(cod_barras, req)


@router.get("/produto/{cod_barras}", response_model=List[ComplementoResponse])
def listar_complementos_produto(
    cod_barras: str,
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
):
    """Lista todos os complementos de um produto específico."""
    logger.info(f"[Complementos] Listar por produto - produto={cod_barras}")
    service = ComplementoService(db)
    return service.listar_complementos_produto(cod_barras, apenas_ativos)


@router.post("/receita/{receita_id}/vincular", response_model=VincularComplementosReceitaResponse, status_code=status.HTTP_200_OK)
def vincular_complementos_receita(
    receita_id: int,
    req: VincularComplementosReceitaRequest,
    db: Session = Depends(get_db),
):
    """Vincula múltiplos complementos a uma receita."""
    logger.info(f"[Complementos] Vincular - receita={receita_id} complementos={req.complemento_ids}")
    service = ComplementoService(db)
    return service.vincular_complementos_receita(receita_id, req)


@router.get("/receita/{receita_id}", response_model=List[ComplementoResponse])
def listar_complementos_receita(
    receita_id: int,
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
):
    """Lista todos os complementos de uma receita específica."""
    logger.info(f"[Complementos] Listar por receita - receita={receita_id}")
    service = ComplementoService(db)
    return service.listar_complementos_receita(receita_id, apenas_ativos)


@router.post("/combo/{combo_id}/vincular", response_model=VincularComplementosComboResponse, status_code=status.HTTP_200_OK)
def vincular_complementos_combo(
    combo_id: int,
    req: VincularComplementosComboRequest,
    db: Session = Depends(get_db),
):
    """Vincula múltiplos complementos a um combo."""
    logger.info(f"[Complementos] Vincular - combo={combo_id} complementos={req.complemento_ids}")
    service = ComplementoService(db)
    return service.vincular_complementos_combo(combo_id, req)


@router.get("/combo/{combo_id}", response_model=List[ComplementoResponse])
def listar_complementos_combo(
    combo_id: int,
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
):
    """Lista todos os complementos de um combo específico."""
    logger.info(f"[Complementos] Listar por combo - combo={combo_id}")
    service = ComplementoService(db)
    return service.listar_complementos_combo(combo_id, apenas_ativos)


# ------ Vincular Itens a Complementos (N:N) ------
@router.post("/{complemento_id}/itens/vincular", response_model=VincularItensComplementoResponse, status_code=status.HTTP_200_OK)
def vincular_itens_complemento(
    complemento_id: int = Path(..., description="ID do complemento"),
    req: VincularItensComplementoRequest,
    db: Session = Depends(get_db),
):
    """
    Vincula múltiplos itens a um complemento.
    
    Este endpoint permite vincular vários itens adicionais a um complemento de uma vez.
    O complemento pode ter configurações de quantidade mínima e máxima de itens
    (`minimo_itens` e `maximo_itens`), que controlam quantos itens o cliente pode escolher.
    
    **Parâmetros do request:**
    - `items`: Lista de itens a vincular (obrigatório). Cada item deve ter:
      - `tipo`: "produto", "receita" ou "combo"
      - Exatamente um de: `produto_cod_barras`, `receita_id`, `combo_id`
      - `ordem`: Ordem de exibição (opcional)
      - `preco_complemento`: Preço específico neste complemento (opcional)
    - `ordens`: Lista de ordens de exibição (opcional, sobrescreve ordem dos items)
    - `precos`: Lista de preços específicos por item (opcional, sobrescreve preco_complemento dos items)
    
    **Comportamento:**
    - Remove todas as vinculações existentes do complemento e cria novas
    - Valida que todos os itens e o complemento pertencem à mesma empresa
    
    **Validações do complemento:**
    - O complemento pode ter `minimo_itens` e `maximo_itens` configurados
    - Essas configurações controlam a quantidade de itens que podem ser selecionados pelo cliente
    - Não afetam a vinculação de itens ao complemento (apenas a seleção pelo cliente)
    """
    logger.info(f"[Complementos] Vincular itens - complemento={complemento_id} quantidade_itens={len(req.items)}")
    service = ComplementoService(db)
    return service.vincular_itens_complemento(complemento_id, req)


@router.post("/{complemento_id}/itens/adicionar", response_model=VincularItemComplementoResponse, status_code=status.HTTP_201_CREATED)
def vincular_item_complemento(
    complemento_id: int = Path(..., description="ID do complemento"),
    req: VincularItemComplementoRequest,
    db: Session = Depends(get_db),
):
    """
    Vincula um único item adicional a um complemento.
    
    Este endpoint permite adicionar um item adicional a um complemento existente. O complemento
    pode ter configurações de quantidade mínima e máxima de itens (`minimo_itens` e `maximo_itens`),
    que controlam quantos itens o cliente pode escolher dentro deste complemento.
    
    **Parâmetros do request:**
    - `tipo`: Tipo do item - "produto", "receita" ou "combo" (obrigatório)
    - Exatamente um de: `produto_cod_barras`, `receita_id`, `combo_id` (obrigatório)
    - `ordem`: Ordem de exibição do item no complemento (opcional, usa a maior ordem + 1 se não informado)
    - `preco_complemento`: Preço específico do item neste complemento (opcional, sobrescreve o preço padrão)
    
    **Comportamento:**
    - Se o item já estiver vinculado ao complemento, atualiza a ordem e/ou preço
    - Se o item não estiver vinculado, cria uma nova vinculação
    - Valida que o item e o complemento pertencem à mesma empresa
    
    **Validações do complemento:**
    - O complemento pode ter `minimo_itens` e `maximo_itens` configurados
    - Essas configurações controlam a quantidade de itens que podem ser selecionados pelo cliente
    - Não afetam a vinculação de itens ao complemento (apenas a seleção pelo cliente)
    """
    item_identificador = req.produto_cod_barras or req.receita_id or req.combo_id
    logger.info(f"[Complementos] Vincular item - complemento={complemento_id} tipo={req.tipo} identificador={item_identificador}")
    service = ComplementoService(db)
    return service.vincular_item_complemento(complemento_id, req)


@router.delete("/{complemento_id}/itens/{item_id}", status_code=status.HTTP_200_OK)
def desvincular_item_complemento(
    complemento_id: int = Path(..., description="ID do complemento"),
    item_id: int = Path(..., description="ID do item"),
    db: Session = Depends(get_db),
):
    """Remove a vinculação de um item com um complemento."""
    logger.info(f"[Complementos] Desvincular item - complemento={complemento_id} item={item_id}")
    service = ComplementoService(db)
    service.desvincular_item_complemento(complemento_id, item_id)
    return {"message": "Item desvinculado com sucesso"}


@router.get("/{complemento_id}/itens", response_model=List[AdicionalResponse])
def listar_itens_complemento(
    complemento_id: int = Path(..., description="ID do complemento"),
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
):
    """Lista todos os itens vinculados a um complemento."""
    logger.info(f"[Complementos] Listar itens - complemento={complemento_id}")
    service = ComplementoService(db)
    return service.listar_itens_complemento(complemento_id, apenas_ativos)


@router.put("/{complemento_id}/itens/ordem", status_code=status.HTTP_200_OK)
def atualizar_ordem_itens(
    complemento_id: int = Path(..., description="ID do complemento"),
    req: AtualizarOrdemItensRequest = Depends(),
    db: Session = Depends(get_db),
):
    """Atualiza a ordem dos itens em um complemento."""
    logger.info(f"[Complementos] Atualizar ordem itens - complemento={complemento_id}")
    service = ComplementoService(db)
    service.atualizar_ordem_itens(complemento_id, req)
    return {"message": "Ordem dos itens atualizada com sucesso"}


@router.put(
    "/{complemento_id}/itens/{item_id}/preco",
    response_model=AdicionalResponse,
    status_code=status.HTTP_200_OK,
)
def atualizar_preco_item_complemento(
    complemento_id: int = Path(..., description="ID do complemento"),
    item_id: int = Path(..., description="ID do item adicional"),
    req: AtualizarPrecoItemComplementoRequest = Depends(),
    db: Session = Depends(get_db),
):
    """Atualiza o preço de um item **apenas dentro deste complemento**.

    - Não altera o preço padrão do adicional cadastrado.
    - O campo `preco` retornado no `AdicionalResponse` já reflete o preço efetivo no complemento.
    """
    logger.info(f"[Complementos] Atualizar preço item - complemento={complemento_id} item={item_id}")
    service = ComplementoService(db)
    return service.atualizar_preco_item_complemento(complemento_id, item_id, req)

