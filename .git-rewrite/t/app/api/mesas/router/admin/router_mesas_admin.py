from fastapi import (
    APIRouter, Depends, HTTPException, status, Path, Query
)
from sqlalchemy.orm import Session
from typing import Optional, List

from app.api.cadastros.models.user_model import UserModel
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.mesas.repositories.repo_mesas import MesaRepository
from app.api.mesas.services.service_mesas import MesaService
from app.api.mesas.schemas.schema_mesa import (
    MesaIn, MesaOut, MesaUpdate, MesaSearchOut, MesaListOut,
    MesaStatsOut, MesaStatusUpdate, StatusMesaEnum, MesaPedidoResumo
)
from app.api.mesas.repositories.repo_pedidos_mesa import PedidoMesaRepository
from app.api.mesas.schemas.schema_pedido_mesa import StatusPedidoMesaEnum
from app.api.mesas.schemas.schema_mesa_historico import HistoricoDaMesaResponse, MesaHistoricoOut
from app.api.mesas.models.model_mesa import StatusMesa
from app.api.mesas.models.model_mesa_historico import MesaHistoricoModel
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/mesas/admin/mesas",
    tags=["Admin - Mesas"],
    dependencies=[Depends(get_current_user)]
)

# -------- ESTATÍSTICAS --------
@router.get("/stats", response_model=MesaStatsOut)
def get_mesa_stats(
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
):
    """Retorna estatísticas das mesas"""
    service = MesaService(db)
    stats = service.get_stats(empresa_id=empresa_id)
    return MesaStatsOut(**stats)

# -------- BUSCA --------
@router.get("/search", response_model=List[MesaSearchOut])
def search_mesas(
    q: Optional[str] = Query(None, description="Termo de busca por número/descrição"),
    ativa: Optional[bool] = Query(None, description="Filtrar por status ativo"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
):
    """Busca mesas com filtros"""
    service = MesaService(db)
    
    mesas = service.search(
        q=q, 
        ativa=ativa, 
        limit=limit, 
        offset=offset,
        empresa_id=empresa_id,
    )
    
    return [
        MesaSearchOut(
            id=m.id,
            empresa_id=m.empresa_id,
            codigo=m.codigo,
            numero=m.numero,
            descricao=m.descricao,
            capacidade=m.capacidade,
            status=StatusMesaEnum(m.status.value if hasattr(m.status, 'value') else m.status),
            status_descricao=m.status_descricao,
            ativa=m.ativa
        )
        for m in mesas
    ]

# -------- LISTAR --------
@router.get("", response_model=List[MesaListOut])
def list_mesas(
    ativa: Optional[bool] = Query(None, description="Filtrar por status ativo"),
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
):
    """Lista todas as mesas"""
    service = MesaService(db)
    mesas = service.list_all(ativa, empresa_id=empresa_id)
    repo_ped = PedidoMesaRepository(db)
    
    result = []
    for m in mesas:
        pedidos_abertos = repo_ped.list_abertos_by_mesa(m.id, empresa_id=empresa_id)
        num_pessoas_atual = None
        if m.is_ocupada and pedidos_abertos:
            num_pessoas_atual = getattr(pedidos_abertos[0], "num_pessoas", None)

        cliente_atual_id = getattr(m.cliente_atual, "id", None) if getattr(m, "cliente_atual", None) else None
        cliente_atual_nome = getattr(m.cliente_atual, "nome", None) if getattr(m, "cliente_atual", None) else None

        fallback_cliente_id = None
        fallback_cliente_nome = None
        pedidos_resumo: list[MesaPedidoResumo] = []

        for p in pedidos_abertos:
            status_value = StatusPedidoMesaEnum(p.status.value if hasattr(p.status, 'value') else p.status)
            pedido_cliente_id = getattr(p, "cliente_id", None)

            pedido_cliente_nome = None
            cliente_rel = getattr(p, "cliente", None)
            if cliente_rel is not None:
                pedido_cliente_nome = getattr(cliente_rel, "nome", None)

            if not pedido_cliente_nome:
                for attr in ("cliente_nome", "nome_cliente", "cliente_nome_manual", "nome_cliente_manual"):
                    valor_attr = getattr(p, attr, None)
                    if valor_attr:
                        pedido_cliente_nome = valor_attr
                        break

            pedidos_resumo.append(
                MesaPedidoResumo(
                    id=p.id,
                    numero_pedido=p.numero_pedido,
                    status=status_value,
                    num_pessoas=getattr(p, "num_pessoas", None),
                    valor_total=float(p.valor_total or 0),
                    cliente_id=pedido_cliente_id,
                    cliente_nome=pedido_cliente_nome,
                )
            )

            if fallback_cliente_nome is None and pedido_cliente_nome:
                fallback_cliente_id = pedido_cliente_id
                fallback_cliente_nome = pedido_cliente_nome

        if not cliente_atual_nome and fallback_cliente_nome:
            cliente_atual_id = fallback_cliente_id
            cliente_atual_nome = fallback_cliente_nome

        result.append(
            MesaListOut(
                id=m.id,
                empresa_id=m.empresa_id,
                codigo=m.codigo,
                numero=m.numero,
                descricao=m.descricao,
                capacidade=m.capacidade,
                status=StatusMesaEnum(m.status.value if hasattr(m.status, 'value') else m.status),
                status_descricao=m.status_descricao,
                ativa=m.ativa,
                label=m.label,
                num_pessoas_atual=num_pessoas_atual,
                cliente_atual_id=cliente_atual_id,
                cliente_atual_nome=cliente_atual_nome,
                pedidos_abertos=pedidos_resumo,
            )
        )

    return result

# -------- BUSCAR POR ID --------
@router.get("/{mesa_id}", response_model=MesaOut)
def get_mesa(
    mesa_id: int = Path(..., title="ID da mesa"),
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
):
    """Busca mesa por ID"""
    service = MesaService(db)
    mesa = service.get_by_id(mesa_id, empresa_id=empresa_id)
    
    return MesaOut(
        id=mesa.id,
        empresa_id=mesa.empresa_id,
        codigo=mesa.codigo,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value if hasattr(mesa.status, 'value') else mesa.status),
        status_descricao=mesa.status_descricao,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada
    )

# -------- CRIAR --------
@router.post(
    "",
    response_model=MesaOut,
    status_code=status.HTTP_201_CREATED
)
def criar_mesa(
    body: MesaIn,
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
):
    """Cria uma nova mesa"""
    logger.info(f"[Mesas Admin] Criando mesa - codigo={body.codigo}, capacidade={body.capacidade}")

    if body.empresa_id != empresa_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "empresa_id do corpo deve corresponder ao parâmetro informado."
        )
    
    service = MesaService(db)
    try:
        mesa = service.create(body)
    except HTTPException as e:
        logger.error(f"[Mesas Admin] Erro ao criar mesa: {e}")
        raise e
    except Exception as e:
        logger.error(f"[Mesas Admin] Erro inesperado ao criar mesa: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao criar mesa: {str(e)}")
    
    logger.info(f"[Mesas Admin] Mesa criada com sucesso - id={mesa.id}")
    
    return MesaOut(
        id=mesa.id,
        empresa_id=mesa.empresa_id,
        codigo=mesa.codigo,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value if hasattr(mesa.status, 'value') else mesa.status),
        status_descricao=mesa.status_descricao,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada
    )

# -------- ATUALIZAR --------
@router.put(
    "/{mesa_id}",
    response_model=MesaOut
)
def atualizar_mesa(
    mesa_id: int,
    body: MesaUpdate,
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
):
    """Atualiza uma mesa"""
    logger.info(f"[Mesas Admin] Atualizando mesa - id={mesa_id}")
    
    if body.empresa_id is not None and body.empresa_id != empresa_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "empresa_id do corpo deve corresponder ao parâmetro informado."
        )
    
    service = MesaService(db)
    try:
        mesa = service.update(mesa_id, body, empresa_id=empresa_id)
    except HTTPException as e:
        logger.error(f"[Mesas Admin] Erro ao atualizar mesa: {e}")
        raise e
    except Exception as e:
        logger.error(f"[Mesas Admin] Erro inesperado ao atualizar mesa: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao atualizar mesa: {str(e)}")
    
    return MesaOut(
        id=mesa.id,
        empresa_id=mesa.empresa_id,
        codigo=mesa.codigo,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value if hasattr(mesa.status, 'value') else mesa.status),
        status_descricao=mesa.status_descricao,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada
    )

# -------- ATUALIZAR STATUS --------
@router.patch(
    "/{mesa_id}/status",
    response_model=MesaOut
)
def atualizar_status_mesa(
    mesa_id: int,
    body: MesaStatusUpdate,
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
):
    """Atualiza apenas o status da mesa"""
    logger.info(f"[Mesas Admin] Atualizando status da mesa - id={mesa_id}, status={body.status}")
    
    service = MesaService(db)
    try:
        mesa = service.update_status(mesa_id, body.status, empresa_id=empresa_id)
    except HTTPException as e:
        logger.error(f"[Mesas Admin] Erro ao atualizar status da mesa: {e}")
        raise e
    except Exception as e:
        logger.error(f"[Mesas Admin] Erro inesperado ao atualizar status da mesa: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao atualizar status da mesa: {str(e)}")
    
    return MesaOut(
        id=mesa.id,
        empresa_id=mesa.empresa_id,
        codigo=mesa.codigo,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value if hasattr(mesa.status, 'value') else mesa.status),
        status_descricao=mesa.status_descricao,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada
    )

# -------- DELETAR --------
@router.delete(
    "/{mesa_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def deletar_mesa(
    mesa_id: int = Path(..., title="ID da mesa"),
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
):
    """Deleta uma mesa"""
    logger.info(f"[Mesas Admin] Deletando mesa - id={mesa_id}")
    
    service = MesaService(db)
    try:
        service.delete(mesa_id, empresa_id=empresa_id)
    except HTTPException as e:
        logger.error(f"[Mesas Admin] Erro ao deletar mesa: {e}")
        raise e
    except Exception as e:
        logger.error(f"[Mesas Admin] Erro inesperado ao deletar mesa: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao deletar mesa: {str(e)}")
    
    logger.info(f"[Mesas Admin] Mesa deletada com sucesso - id={mesa_id}")
    return None

# -------- OPERAÇÕES DE STATUS --------
@router.post(
    "/{mesa_id}/ocupar",
    response_model=MesaOut
)
def ocupar_mesa(
    mesa_id: int = Path(..., title="ID da mesa"),
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
):
    """Ocupa uma mesa"""
    logger.info(f"[Mesas Admin] Ocupando mesa - id={mesa_id}")
    
    service = MesaService(db)
    try:
        mesa = service.ocupar_mesa_se_disponivel(mesa_id, empresa_id=empresa_id)
    except ValueError as e:
        logger.warning(f"[Mesas Admin] Mesa não pode ser ocupada: {e}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        logger.error(f"[Mesas Admin] Erro ao ocupar mesa: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao ocupar mesa: {str(e)}")
    
    return MesaOut(
        id=mesa.id,
        empresa_id=mesa.empresa_id,
        codigo=mesa.codigo,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value if hasattr(mesa.status, 'value') else mesa.status),
        status_descricao=mesa.status_descricao,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada
    )

@router.post(
    "/{mesa_id}/liberar",
    response_model=MesaOut
)
def liberar_mesa(
    mesa_id: int = Path(..., title="ID da mesa"),
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
):
    """Libera uma mesa"""
    logger.info(f"[Mesas Admin] Liberando mesa - id={mesa_id}")
    
    service = MesaService(db)
    try:
        mesa = service.liberar_mesa_se_ocupada(mesa_id, empresa_id=empresa_id)
    except ValueError as e:
        logger.warning(f"[Mesas Admin] Mesa não pode ser liberada: {e}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        logger.error(f"[Mesas Admin] Erro ao liberar mesa: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao liberar mesa: {str(e)}")
    
    return MesaOut(
        id=mesa.id,
        empresa_id=mesa.empresa_id,
        codigo=mesa.codigo,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value if hasattr(mesa.status, 'value') else mesa.status),
        status_descricao=mesa.status_descricao,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada
    )

@router.post(
    "/{mesa_id}/reservar",
    response_model=MesaOut
)
def reservar_mesa(
    mesa_id: int = Path(..., title="ID da mesa"),
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
):
    """Reserva uma mesa"""
    logger.info(f"[Mesas Admin] Reservando mesa - id={mesa_id}")
    
    service = MesaService(db)
    try:
        mesa = service.reservar_mesa_se_disponivel(mesa_id, empresa_id=empresa_id)
    except ValueError as e:
        logger.warning(f"[Mesas Admin] Mesa não pode ser reservada: {e}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        logger.error(f"[Mesas Admin] Erro ao reservar mesa: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao reservar mesa: {str(e)}")
    
    return MesaOut(
        id=mesa.id,
        codigo=mesa.codigo,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value if hasattr(mesa.status, 'value') else mesa.status),
        status_descricao=mesa.status_descricao,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada
    )


# ======================================================================
# ================= OBTER HISTÓRICO DA MESA ============================
@router.get(
    "/{mesa_id}/historico",
    response_model=HistoricoDaMesaResponse,
    status_code=status.HTTP_200_OK,
)
def obter_historico_mesa(
    mesa_id: int = Path(..., description="ID da mesa", gt=0),
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
):
    """
    Obtém o histórico completo de operações de uma mesa.
    
    - **mesa_id**: ID da mesa (obrigatório, deve ser maior que 0)
    
    Retorna todos os registros de operações com timestamps, descrições e observações.
    """
    logger.info(f"[Mesas Admin] Obter histórico - mesa_id={mesa_id}")
    
    # Verifica se a mesa existe
    service = MesaService(db)
    mesa = service.get_by_id(mesa_id, empresa_id=empresa_id)
    if not mesa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mesa com ID {mesa_id} não encontrada"
        )
    
    # Busca o histórico da mesa
    historicos = service.get_historico(mesa_id, empresa_id=empresa_id)
    
    return HistoricoDaMesaResponse(
        mesa_id=mesa_id,
        historicos=[
            MesaHistoricoOut(
                id=h.id,
                mesa_id=h.mesa_id,
                cliente_id=h.cliente_id,
                usuario_id=h.usuario_id,
                tipo_operacao=h.tipo_operacao,
                status_anterior=h.status_anterior,
                status_novo=h.status_novo,
                descricao=h.descricao,
                observacoes=h.observacoes,
                ip_origem=h.ip_origem,
                user_agent=h.user_agent,
                created_at=h.created_at,
                tipo_operacao_descricao=h.tipo_operacao_descricao,
                resumo_operacao=h.resumo_operacao,
                usuario=h.usuario.nome if h.usuario else None,
            )
            for h in historicos
        ]
    )

