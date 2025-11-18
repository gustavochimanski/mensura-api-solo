from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ....database.db_connection import get_db
from ....core.admin_dependencies import get_current_user
from ..core.event_publisher import EventPublisher
from ..core.event_bus import event_bus
from ..repositories.event_repository import EventRepository
from ..schemas.event_schemas import (
    CreateEventRequest,
    ProcessEventRequest,
    EventResponse,
    EventListResponse,
    EventFilter
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])

def get_event_repository(db: Session = Depends(get_db)) -> EventRepository:
    """Dependency para obter o repositório de eventos"""
    return EventRepository(db)

def get_event_publisher() -> EventPublisher:
    """Dependency para obter o publisher de eventos"""
    return EventPublisher(event_bus)

@router.post("/", response_model=EventResponse)
async def create_event(
    request: CreateEventRequest,
    publisher: EventPublisher = Depends(get_event_publisher),
    current_user = Depends(get_current_user)
):
    """Cria um novo evento"""
    try:
        event_id = await publisher.publish_event(
            empresa_id=request.empresa_id,
            event_type=request.event_type,
            data=request.data,
            event_id=request.event_id,
            event_metadata=request.event_metadata
        )
        
        return {"id": event_id, "message": "Evento criado com sucesso"}
    except Exception as e:
        logger.error(f"Erro ao criar evento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pedido-criado")
async def publish_pedido_criado(
    empresa_id: str,
    pedido_id: str,
    cliente_data: dict,
    itens: list,
    valor_total: float,
    event_metadata: Optional[dict] = None,
    publisher: EventPublisher = Depends(get_event_publisher),
    current_user = Depends(get_current_user)
):
    """Publica evento de pedido criado"""
    try:
        event_id = await publisher.publish_pedido_criado(
            empresa_id=empresa_id,
            pedido_id=pedido_id,
            cliente_data=cliente_data,
            itens=itens,
            valor_total=valor_total,
            event_metadata=event_metadata
        )
        
        return {"id": event_id, "message": "Evento de pedido criado publicado"}
    except Exception as e:
        logger.error(f"Erro ao publicar evento de pedido criado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pedido-aprovado")
async def publish_pedido_aprovado(
    empresa_id: str,
    pedido_id: str,
    aprovado_por: str,
    event_metadata: Optional[dict] = None,
    publisher: EventPublisher = Depends(get_event_publisher),
    current_user = Depends(get_current_user)
):
    """Publica evento de pedido aprovado"""
    try:
        event_id = await publisher.publish_pedido_aprovado(
            empresa_id=empresa_id,
            pedido_id=pedido_id,
            aprovado_por=aprovado_por,
            event_metadata=event_metadata
        )
        
        return {"id": event_id, "message": "Evento de pedido aprovado publicado"}
    except Exception as e:
        logger.error(f"Erro ao publicar evento de pedido aprovado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/estoque-baixo")
async def publish_estoque_baixo(
    empresa_id: str,
    produto_id: str,
    produto_nome: str,
    quantidade_atual: int,
    quantidade_minima: int,
    event_metadata: Optional[dict] = None,
    publisher: EventPublisher = Depends(get_event_publisher),
    current_user = Depends(get_current_user)
):
    """Publica evento de estoque baixo"""
    try:
        event_id = await publisher.publish_estoque_baixo(
            empresa_id=empresa_id,
            produto_id=produto_id,
            produto_nome=produto_nome,
            quantidade_atual=quantidade_atual,
            quantidade_minima=quantidade_minima,
            event_metadata=event_metadata
        )
        
        return {"id": event_id, "message": "Evento de estoque baixo publicado"}
    except Exception as e:
        logger.error(f"Erro ao publicar evento de estoque baixo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pagamento-aprovado")
async def publish_pagamento_aprovado(
    empresa_id: str,
    pagamento_id: str,
    pedido_id: str,
    valor: float,
    metodo_pagamento: str,
    event_metadata: Optional[dict] = None,
    publisher: EventPublisher = Depends(get_event_publisher),
    current_user = Depends(get_current_user)
):
    """Publica evento de pagamento aprovado"""
    try:
        event_id = await publisher.publish_pagamento_aprovado(
            empresa_id=empresa_id,
            pagamento_id=pagamento_id,
            pedido_id=pedido_id,
            valor=valor,
            metodo_pagamento=metodo_pagamento,
            event_metadata=event_metadata
        )
        
        return {"id": event_id, "message": "Evento de pagamento aprovado publicado"}
    except Exception as e:
        logger.error(f"Erro ao publicar evento de pagamento aprovado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    event_repo: EventRepository = Depends(get_event_repository),
    current_user = Depends(get_current_user)
):
    """Busca evento por ID"""
    event = event_repo.get_by_id(event_id)
    
    if not event:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    
    return EventResponse.from_orm(event)

@router.get("/", response_model=EventListResponse)
async def list_events(
    empresa_id: Optional[str] = Query(None, description="ID da empresa"),
    event_type: Optional[str] = Query(None, description="Tipo do evento"),
    processed: Optional[bool] = Query(None, description="Status de processamento"),
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(50, ge=1, le=100, description="Itens por página"),
    event_repo: EventRepository = Depends(get_event_repository),
    current_user = Depends(get_current_user)
):
    """Lista eventos com filtros"""
    try:
        filters = EventFilter(
            empresa_id=empresa_id,
            event_type=event_type,
            processed=processed
        )
        
        offset = (page - 1) * per_page
        events = event_repo.filter_events(filters, per_page, offset)
        total = event_repo.count_events(filters)
        
        event_responses = [EventResponse.from_orm(e) for e in events]
        
        return EventListResponse(
            events=event_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=(total + per_page - 1) // per_page
        )
    except Exception as e:
        logger.error(f"Erro ao listar eventos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/empresa/{empresa_id}", response_model=List[EventResponse])
async def get_empresa_events(
    empresa_id: str,
    limit: int = Query(100, ge=1, le=500, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset"),
    event_repo: EventRepository = Depends(get_event_repository),
    current_user = Depends(get_current_user)
):
    """Busca eventos de uma empresa"""
    try:
        events = event_repo.get_by_empresa(empresa_id, limit, offset)
        return [EventResponse.from_orm(e) for e in events]
    except Exception as e:
        logger.error(f"Erro ao buscar eventos da empresa: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics/{empresa_id}")
async def get_event_statistics(
    empresa_id: str,
    days: int = Query(30, ge=1, le=365, description="Período em dias"),
    event_repo: EventRepository = Depends(get_event_repository),
    current_user = Depends(get_current_user)
):
    """Retorna estatísticas de eventos de uma empresa"""
    try:
        statistics = event_repo.get_event_statistics(empresa_id, days)
        return statistics
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas de eventos: {e}")
        raise HTTPException(status_code=500, detail=str(e))
