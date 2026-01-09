from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, status, Query, Path, Body, HTTPException
from sqlalchemy.orm import Session

from app.api.caixas.services.service_caixa_abertura import CaixaAberturaService
from app.api.caixas.schemas.schema_caixa import (
    CaixaAberturaCreate,
    CaixaAberturaFechamentoRequest,
    CaixaAberturaResponse,
    CaixaAberturaResumoResponse,
    CaixaAberturaValoresEsperadosResponse,
    CaixaAberturaConferenciaResumoResponse,
    RetiradaCreate,
    RetiradaResponse
)
from app.api.cadastros.models.user_model import UserModel
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/caixa/admin/aberturas",
    tags=["Admin - Aberturas de Caixa"],
    dependencies=[Depends(get_current_user)]
)

# ======================================================================
# ============================ ABRIR CAIXA =============================
@router.post("/abrir", response_model=CaixaAberturaResponse, status_code=status.HTTP_201_CREATED)
def abrir_caixa(
    data: CaixaAberturaCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Abre uma nova abertura de caixa.
    
    - **caixa_id**: ID do caixa cadastrado (obrigatório)
    - **empresa_id**: ID da empresa (obrigatório)
    - **valor_inicial**: Valor em dinheiro no caixa (obrigatório, >= 0)
    - **data_hora_abertura**: Data e hora da abertura (opcional, usa timestamp atual se não informado)
    - **observacoes_abertura**: Observações opcionais
    
    Não permite abrir uma nova abertura se já existir uma abertura aberta para o caixa.
    """
    logger.info(f"[CaixaAbertura] Abrir - caixa_id={data.caixa_id} empresa_id={data.empresa_id} usuario_id={current_user.id}")
    svc = CaixaAberturaService(db)
    return svc.abrir_caixa(data, current_user.id)

# ======================================================================
# ============================ FECHAR CAIXA ============================
@router.post("/{caixa_abertura_id}/fechar", response_model=CaixaAberturaResponse, status_code=status.HTTP_200_OK)
def fechar_caixa(
    caixa_abertura_id: int = Path(..., description="ID da abertura a ser fechada", gt=0),
    data: CaixaAberturaFechamentoRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Fecha uma abertura de caixa aberta.
    
    - **saldo_real**: Valor real contado no fechamento para dinheiro físico (obrigatório, >= 0)
    - **data_hora_fechamento**: Data e hora do fechamento (opcional, usa timestamp atual se não informado)
    - **observacoes_fechamento**: Observações opcionais
    - **conferencias**: Lista de conferências por tipo de meio de pagamento (opcional)
        - Cada conferência deve ter: meio_pagamento_id, valor_conferido, observacoes (opcional)
    
    Calcula automaticamente o saldo esperado e a diferença entre esperado e real.
    """
    logger.info(f"[CaixaAbertura] Fechar - caixa_abertura_id={caixa_abertura_id} usuario_id={current_user.id}")
    svc = CaixaAberturaService(db)
    return svc.fechar_caixa(caixa_abertura_id, data, current_user.id)

# ======================================================================
# ======================= BUSCAR ABERTURA POR ID =======================
@router.get("/{caixa_abertura_id}", response_model=CaixaAberturaResponse, status_code=status.HTTP_200_OK)
def get_abertura(
    caixa_abertura_id: int = Path(..., description="ID da abertura", gt=0),
    db: Session = Depends(get_db),
):
    """
    Busca uma abertura de caixa específica por ID com todas as informações.
    """
    svc = CaixaAberturaService(db)
    return svc.get_by_id(caixa_abertura_id)

# ======================================================================
# ===================== BUSCAR ABERTURA ABERTA ========================
@router.get("/aberto/{empresa_id}", response_model=CaixaAberturaResponse, status_code=status.HTTP_200_OK)
def get_abertura_aberta(
    empresa_id: int = Path(..., description="ID da empresa", gt=0),
    caixa_id: Optional[int] = Query(None, description="ID do caixa (opcional)", gt=0),
    db: Session = Depends(get_db),
):
    """
    Busca a abertura aberta de uma empresa.
    Opcionalmente pode filtrar por caixa_id específico.
    Retorna 404 se não houver abertura aberta.
    """
    logger.info(f"[CaixaAbertura] Buscar aberta - empresa_id={empresa_id} caixa_id={caixa_id}")
    svc = CaixaAberturaService(db)
    abertura = svc.get_caixa_aberto(empresa_id, caixa_id)
    if not abertura:
        logger.warning(f"[CaixaAbertura] Nenhuma abertura aberta encontrada - empresa_id={empresa_id} caixa_id={caixa_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não há abertura aberta para esta empresa"
        )
    logger.info(f"[CaixaAbertura] Abertura aberta encontrada - abertura_id={abertura.id} empresa_id={empresa_id}")
    return abertura

# ======================================================================
# ========================= LISTAR ABERTURAS ===========================
@router.get("/", response_model=List[CaixaAberturaResumoResponse], status_code=status.HTTP_200_OK)
def listar_aberturas(
    empresa_id: Optional[int] = Query(None, description="Filtrar por empresa", gt=0),
    caixa_id: Optional[int] = Query(None, description="Filtrar por caixa", gt=0),
    status_filtro: Optional[str] = Query(None, alias="status", description="Filtrar por status (ABERTO/FECHADO)"),
    data_inicio: Optional[date] = Query(None, description="Data início (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Data fim (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(100, ge=1, le=500, description="Limite de registros"),
    db: Session = Depends(get_db),
):
    """
    Lista aberturas de caixa com filtros opcionais.
    
    Filtros disponíveis:
    - **empresa_id**: Filtrar por empresa
    - **caixa_id**: Filtrar por caixa cadastrado
    - **status**: Filtrar por status (ABERTO/FECHADO)
    - **data_inicio**: Data de início para filtrar por data de abertura
    - **data_fim**: Data de fim para filtrar por data de abertura
    """
    svc = CaixaAberturaService(db)
    return svc.list(
        empresa_id=empresa_id,
        caixa_id=caixa_id,
        status=status_filtro,
        data_inicio=data_inicio,
        data_fim=data_fim,
        skip=skip,
        limit=limit
    )

# ======================================================================
# =================== RECALCULAR SALDO ESPERADO =======================
@router.post("/{caixa_abertura_id}/recalcular-saldo", response_model=CaixaAberturaResponse, status_code=status.HTTP_200_OK)
def recalcular_saldo(
    caixa_abertura_id: int = Path(..., description="ID da abertura", gt=0),
    db: Session = Depends(get_db),
):
    """
    Recalcula o saldo esperado da abertura baseado em:
    - Valor inicial
    + Entradas (pedidos pagos em dinheiro desde a abertura)
    - Saídas (trocos dados desde a abertura)
    
    Só funciona para aberturas abertas.
    """
    logger.info(f"[CaixaAbertura] Recalcular saldo - caixa_abertura_id={caixa_abertura_id}")
    svc = CaixaAberturaService(db)
    return svc.calcular_saldo_esperado(caixa_abertura_id)

# ======================================================================
# ============ VALORES ESPERADOS POR TIPO DE PAGAMENTO ================
@router.get("/{caixa_abertura_id}/valores-esperados", response_model=CaixaAberturaValoresEsperadosResponse, status_code=status.HTTP_200_OK)
def get_valores_esperados(
    caixa_abertura_id: int = Path(..., description="ID da abertura aberta", gt=0),
    db: Session = Depends(get_db),
):
    """
    Retorna valores esperados por tipo de meio de pagamento para uma abertura aberta.
    
    Útil antes do fechamento para conferência. Mostra:
    - Valor inicial em dinheiro
    - Valores esperados por cada meio de pagamento usado
    - Quantidade de transações por meio de pagamento
    - Total esperado em dinheiro (valor inicial + entradas - saídas)
    
    Só funciona para aberturas abertas.
    """
    logger.info(f"[CaixaAbertura] Valores esperados - caixa_abertura_id={caixa_abertura_id}")
    svc = CaixaAberturaService(db)
    return svc.get_valores_esperados(caixa_abertura_id)

# ======================================================================
# ================== CONFERÊNCIAS DA ABERTURA FECHADA =================
@router.get("/{caixa_abertura_id}/conferencias", response_model=CaixaAberturaConferenciaResumoResponse, status_code=status.HTTP_200_OK)
def get_conferencias(
    caixa_abertura_id: int = Path(..., description="ID da abertura", gt=0),
    db: Session = Depends(get_db),
):
    """
    Retorna todas as conferências de uma abertura fechada.
    
    Mostra para cada meio de pagamento:
    - Valor esperado (calculado automaticamente)
    - Valor conferido (informado no fechamento)
    - Diferença entre esperado e conferido
    - Quantidade de transações
    - Observações
    """
    logger.info(f"[CaixaAbertura] Conferências - caixa_abertura_id={caixa_abertura_id}")
    svc = CaixaAberturaService(db)
    return svc.get_conferencias(caixa_abertura_id)

# ======================================================================
# ======================= RETIRADAS DA ABERTURA ========================
@router.post("/{caixa_abertura_id}/retiradas", response_model=RetiradaResponse, status_code=status.HTTP_201_CREATED)
def criar_retirada(
    caixa_abertura_id: int = Path(..., description="ID da abertura", gt=0),
    data: RetiradaCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Registra uma retirada da abertura (sangria ou despesa).
    
    - **tipo**: Tipo de retirada (SANGRIA ou DESPESA)
    - **valor**: Valor da retirada (obrigatório, > 0)
    - **observacoes**: Observações (obrigatório para DESPESA, opcional para SANGRIA)
    
    Apenas aberturas abertas podem receber retiradas.
    """
    logger.info(f"[CaixaAbertura] Criar retirada - caixa_abertura_id={caixa_abertura_id} tipo={data.tipo} valor={data.valor} usuario_id={current_user.id}")
    svc = CaixaAberturaService(db)
    return svc.criar_retirada(caixa_abertura_id, data, current_user.id)

@router.get("/{caixa_abertura_id}/retiradas", response_model=List[RetiradaResponse], status_code=status.HTTP_200_OK)
def listar_retiradas(
    caixa_abertura_id: int = Path(..., description="ID da abertura", gt=0),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo (SANGRIA ou DESPESA)"),
    db: Session = Depends(get_db),
):
    """
    Lista todas as retiradas de uma abertura.
    
    Query Parameters:
    - **tipo** (opcional): Filtrar por tipo (SANGRIA ou DESPESA)
    """
    logger.info(f"[CaixaAbertura] Listar retiradas - caixa_abertura_id={caixa_abertura_id} tipo={tipo}")
    svc = CaixaAberturaService(db)
    return svc.listar_retiradas(caixa_abertura_id, tipo)

@router.delete("/retiradas/{retirada_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_retirada(
    retirada_id: int = Path(..., description="ID da retirada", gt=0),
    empresa_id: Optional[int] = Query(None, description="ID da empresa para validação", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Exclui uma retirada da abertura.
    
    Apenas retiradas de aberturas abertas podem ser excluídas.
    Após a exclusão, o saldo esperado da abertura é recalculado automaticamente.
    
    Se empresa_id for informado, valida que a retirada pertence à empresa.
    """
    logger.info(f"[CaixaAbertura] Excluir retirada - retirada_id={retirada_id} empresa_id={empresa_id} usuario_id={current_user.id}")
    svc = CaixaAberturaService(db)
    svc.excluir_retirada(retirada_id, empresa_id)
    return None

