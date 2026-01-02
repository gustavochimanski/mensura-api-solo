from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, status, Query, Path, Body
from sqlalchemy.orm import Session

from app.api.caixas.services.service_caixa import CaixaService
from app.api.caixas.schemas.schema_caixa import (
    CaixaCreate,
    CaixaFechamentoRequest,
    CaixaResponse,
    CaixaResumoResponse,
    CaixaValoresEsperadosResponse,
    CaixaConferenciaResumoResponse,
    RetiradaCreate,
    RetiradaResponse
)
from app.api.cadastros.models.user_model import UserModel
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/caixa/admin/caixas",
    tags=["Admin - Caixas"],
    dependencies=[Depends(get_current_user)]
)

# ======================================================================
# ============================ ABRIR CAIXA =============================
@router.post("/abrir", response_model=CaixaResponse, status_code=status.HTTP_201_CREATED)
def abrir_caixa(
    data: CaixaCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Abre um novo caixa para a empresa.
    
    - **empresa_id**: ID da empresa (obrigatório)
    - **valor_inicial**: Valor em dinheiro no caixa (obrigatório, >= 0)
    - **data_hora_abertura**: Data e hora da abertura (opcional, usa timestamp atual se não informado)
    - **observacoes_abertura**: Observações opcionais
    
    Não permite abrir um novo caixa se já existir um caixa aberto para a empresa.
    """
    logger.info(f"[Caixa] Abrir caixa - empresa_id={data.empresa_id} usuario_id={current_user.id}")
    svc = CaixaService(db)
    return svc.abrir_caixa(data, current_user.id)

# ======================================================================
# ============================ FECHAR CAIXA ============================
@router.post("/{caixa_id}/fechar", response_model=CaixaResponse, status_code=status.HTTP_200_OK)
def fechar_caixa(
    caixa_id: int = Path(..., description="ID do caixa a ser fechado", gt=0),
    data: CaixaFechamentoRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Fecha um caixa aberto.
    
    - **caixa_id**: ID do caixa (obrigatório)
    - **saldo_real**: Valor real contado no fechamento para dinheiro físico (obrigatório, >= 0)
    - **data_hora_fechamento**: Data e hora do fechamento (opcional, usa timestamp atual se não informado)
    - **observacoes_fechamento**: Observações opcionais
    - **conferencias**: Lista de conferências por tipo de meio de pagamento (opcional)
        - Cada conferência deve ter: meio_pagamento_id, valor_conferido, observacoes (opcional)
    
    Calcula automaticamente o saldo esperado e a diferença entre esperado e real.
    Para cada meio de pagamento informado, calcula e salva a diferença entre valor esperado e conferido.
    """
    logger.info(f"[Caixa] Fechar caixa - caixa_id={caixa_id} usuario_id={current_user.id}")
    svc = CaixaService(db)
    return svc.fechar_caixa(caixa_id, data, current_user.id)

# ======================================================================
# ======================= BUSCAR CAIXA POR ID ==========================
@router.get("/{caixa_id}", response_model=CaixaResponse, status_code=status.HTTP_200_OK)
def get_caixa(
    caixa_id: int = Path(..., description="ID do caixa", gt=0),
    db: Session = Depends(get_db),
):
    """
    Busca um caixa específico por ID com todas as informações.
    """
    svc = CaixaService(db)
    return svc.get_by_id(caixa_id)

# ======================================================================
# ===================== BUSCAR CAIXA ABERTO ============================
@router.get("/aberto/{empresa_id}", response_model=CaixaResponse, status_code=status.HTTP_200_OK)
def get_caixa_aberto(
    empresa_id: int = Path(..., description="ID da empresa", gt=0),
    db: Session = Depends(get_db),
):
    """
    Busca o caixa aberto de uma empresa.
    Retorna 404 se não houver caixa aberto.
    """
    svc = CaixaService(db)
    caixa = svc.get_caixa_aberto(empresa_id)
    if not caixa:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não há caixa aberto para esta empresa"
        )
    return caixa

# ======================================================================
# ========================= LISTAR CAIXAS ==============================
@router.get("/", response_model=List[CaixaResumoResponse], status_code=status.HTTP_200_OK)
def listar_caixas(
    empresa_id: Optional[int] = Query(None, description="Filtrar por empresa", gt=0),
    status_filtro: Optional[str] = Query(None, alias="status", description="Filtrar por status (ABERTO/FECHADO)"),
    data_inicio: Optional[date] = Query(None, description="Data início (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Data fim (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(100, ge=1, le=500, description="Limite de registros"),
    db: Session = Depends(get_db),
):
    """
    Lista caixas com filtros opcionais.
    
    Filtros disponíveis:
    - **empresa_id**: Filtrar por empresa
    - **status**: Filtrar por status (ABERTO/FECHADO)
    - **data_inicio**: Data de início para filtrar por data de abertura
    - **data_fim**: Data de fim para filtrar por data de abertura
    """
    svc = CaixaService(db)
    return svc.list(
        empresa_id=empresa_id,
        status=status_filtro,
        data_inicio=data_inicio,
        data_fim=data_fim,
        skip=skip,
        limit=limit
    )

# ======================================================================
# =================== RECALCULAR SALDO ESPERADO ========================
@router.post("/{caixa_id}/recalcular-saldo", response_model=CaixaResponse, status_code=status.HTTP_200_OK)
def recalcular_saldo(
    caixa_id: int = Path(..., description="ID do caixa", gt=0),
    db: Session = Depends(get_db),
):
    """
    Recalcula o saldo esperado do caixa baseado em:
    - Valor inicial
    + Entradas (pedidos pagos em dinheiro desde a abertura)
    - Saídas (trocos dados desde a abertura)
    
    Só funciona para caixas abertos.
    """
    logger.info(f"[Caixa] Recalcular saldo - caixa_id={caixa_id}")
    svc = CaixaService(db)
    return svc.calcular_saldo_esperado(caixa_id)

# ======================================================================
# ============ VALORES ESPERADOS POR TIPO DE PAGAMENTO ================
@router.get("/{caixa_id}/valores-esperados", response_model=CaixaValoresEsperadosResponse, status_code=status.HTTP_200_OK)
def get_valores_esperados(
    caixa_id: int = Path(..., description="ID do caixa aberto", gt=0),
    db: Session = Depends(get_db),
):
    """
    Retorna valores esperados por tipo de meio de pagamento para um caixa aberto.
    
    Útil antes do fechamento para conferência. Mostra:
    - Valor inicial em dinheiro
    - Valores esperados por cada meio de pagamento usado
    - Quantidade de transações por meio de pagamento
    - Total esperado em dinheiro (valor inicial + entradas - saídas)
    
    Só funciona para caixas abertos.
    """
    logger.info(f"[Caixa] Valores esperados - caixa_id={caixa_id}")
    svc = CaixaService(db)
    return svc.get_valores_esperados(caixa_id)

# ======================================================================
# ================== CONFERÊNCIAS DO CAIXA FECHADO =====================
@router.get("/{caixa_id}/conferencias", response_model=CaixaConferenciaResumoResponse, status_code=status.HTTP_200_OK)
def get_conferencias(
    caixa_id: int = Path(..., description="ID do caixa", gt=0),
    db: Session = Depends(get_db),
):
    """
    Retorna todas as conferências de um caixa fechado.
    
    Mostra para cada meio de pagamento:
    - Valor esperado (calculado automaticamente)
    - Valor conferido (informado no fechamento)
    - Diferença entre esperado e conferido
    - Quantidade de transações
    - Observações
    """
    logger.info(f"[Caixa] Conferências - caixa_id={caixa_id}")
    svc = CaixaService(db)
    return svc.get_conferencias(caixa_id)

# ======================================================================
# ======================= RETIRADAS DO CAIXA ============================
@router.post("/{caixa_id}/retiradas", response_model=RetiradaResponse, status_code=status.HTTP_201_CREATED)
def criar_retirada(
    caixa_id: int = Path(..., description="ID do caixa", gt=0),
    data: RetiradaCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Registra uma retirada do caixa (sangria ou despesa).
    
    - **tipo**: Tipo de retirada (SANGRIA ou DESPESA)
    - **valor**: Valor da retirada (obrigatório, > 0)
    - **observacoes**: Observações (obrigatório para DESPESA, opcional para SANGRIA)
    
    Apenas caixas abertos podem receber retiradas.
    """
    logger.info(f"[Caixa] Criar retirada - caixa_id={caixa_id} tipo={data.tipo} valor={data.valor} usuario_id={current_user.id}")
    svc = CaixaService(db)
    return svc.criar_retirada(caixa_id, data, current_user.id)

@router.get("/{caixa_id}/retiradas", response_model=List[RetiradaResponse], status_code=status.HTTP_200_OK)
def listar_retiradas(
    caixa_id: int = Path(..., description="ID do caixa", gt=0),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo (SANGRIA ou DESPESA)"),
    db: Session = Depends(get_db),
):
    """
    Lista todas as retiradas de um caixa.
    
    Query Parameters:
    - **tipo** (opcional): Filtrar por tipo (SANGRIA ou DESPESA)
    """
    logger.info(f"[Caixa] Listar retiradas - caixa_id={caixa_id} tipo={tipo}")
    svc = CaixaService(db)
    return svc.listar_retiradas(caixa_id, tipo)

@router.delete("/retiradas/{retirada_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_retirada(
    retirada_id: int = Path(..., description="ID da retirada", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Exclui uma retirada do caixa.
    
    Apenas retiradas de caixas abertos podem ser excluídas.
    Após a exclusão, o saldo esperado do caixa é recalculado automaticamente.
    """
    logger.info(f"[Caixa] Excluir retirada - retirada_id={retirada_id} usuario_id={current_user.id}")
    svc = CaixaService(db)
    svc.excluir_retirada(retirada_id)
    return None

