from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from ..models.event import Event
from ..schemas.event_schemas import EventFilter

logger = logging.getLogger(__name__)

class EventRepository:
    """Repositório para operações com eventos"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, event_data: Dict[str, Any]) -> Event:
        """Cria um novo evento"""
        try:
            event = Event(**event_data)
            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)
            
            logger.info(f"Evento criado: {event.id} - {event.event_type}")
            return event
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar evento: {e}")
            raise
    
    def get_by_id(self, event_id: str) -> Optional[Event]:
        """Busca evento por ID"""
        return self.db.query(Event).filter(Event.id == event_id).first()
    
    def get_unprocessed_events(self, limit: int = 100) -> List[Event]:
        """Busca eventos não processados"""
        return (
            self.db.query(Event)
            .filter(Event.processed == False)
            .order_by(Event.created_at)
            .limit(limit)
            .all()
        )
    
    def get_by_empresa(self, empresa_id: str, limit: int = 100, offset: int = 0) -> List[Event]:
        """Busca eventos por empresa"""
        return (
            self.db.query(Event)
            .filter(Event.empresa_id == empresa_id)
            .order_by(desc(Event.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
    
    def mark_as_processed(self, event_id: str) -> bool:
        """Marca evento como processado"""
        try:
            event = self.get_by_id(event_id)
            if not event:
                return False
            
            event.processed = True
            event.processed_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Evento {event_id} marcado como processado")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao marcar evento {event_id} como processado: {e}")
            return False
    
    def filter_events(self, filters: EventFilter, limit: int = 100, offset: int = 0) -> List[Event]:
        """Filtra eventos com base nos critérios fornecidos"""
        query = self.db.query(Event)
        
        if filters.empresa_id:
            query = query.filter(Event.empresa_id == filters.empresa_id)
        
        if filters.event_type:
            query = query.filter(Event.event_type == filters.event_type)
        
        if filters.processed is not None:
            query = query.filter(Event.processed == filters.processed)
        
        if filters.created_from:
            query = query.filter(Event.created_at >= filters.created_from)
        
        if filters.created_to:
            query = query.filter(Event.created_at <= filters.created_to)
        
        return (
            query.order_by(desc(Event.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
    
    def count_events(self, filters: EventFilter) -> int:
        """Conta eventos com base nos filtros"""
        query = self.db.query(Event)
        
        if filters.empresa_id:
            query = query.filter(Event.empresa_id == filters.empresa_id)
        
        if filters.event_type:
            query = query.filter(Event.event_type == filters.event_type)
        
        if filters.processed is not None:
            query = query.filter(Event.processed == filters.processed)
        
        if filters.created_from:
            query = query.filter(Event.created_at >= filters.created_from)
        
        if filters.created_to:
            query = query.filter(Event.created_at <= filters.created_to)
        
        return query.count()
    
    def get_events_by_type(self, event_type: str, limit: int = 100) -> List[Event]:
        """Busca eventos por tipo"""
        return (
            self.db.query(Event)
            .filter(Event.event_type == event_type)
            .order_by(desc(Event.created_at))
            .limit(limit)
            .all()
        )
    
    def get_events_by_empresa_and_type(self, empresa_id: str, event_type: str, limit: int = 100) -> List[Event]:
        """Busca eventos por empresa e tipo"""
        return (
            self.db.query(Event)
            .filter(
                and_(
                    Event.empresa_id == empresa_id,
                    Event.event_type == event_type
                )
            )
            .order_by(desc(Event.created_at))
            .limit(limit)
            .all()
        )
    
    def delete_old_events(self, days: int = 30) -> int:
        """Remove eventos antigos"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        try:
            deleted_count = (
                self.db.query(Event)
                .filter(
                    and_(
                        Event.created_at < cutoff_date,
                        Event.processed == True
                    )
                )
                .delete()
            )
            self.db.commit()
            logger.info(f"Removidos {deleted_count} eventos antigos")
            return deleted_count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao remover eventos antigos: {e}")
            return 0
    
    def get_event_statistics(self, empresa_id: str, days: int = 30) -> Dict[str, Any]:
        """Retorna estatísticas de eventos"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        try:
            # Total de eventos
            total_events = (
                self.db.query(Event)
                .filter(
                    and_(
                        Event.empresa_id == empresa_id,
                        Event.created_at >= cutoff_date
                    )
                )
                .count()
            )
            
            # Eventos processados
            processed_events = (
                self.db.query(Event)
                .filter(
                    and_(
                        Event.empresa_id == empresa_id,
                        Event.created_at >= cutoff_date,
                        Event.processed == True
                    )
                )
                .count()
            )
            
            # Eventos por tipo
            events_by_type = (
                self.db.query(Event.event_type, func.count(Event.id))
                .filter(
                    and_(
                        Event.empresa_id == empresa_id,
                        Event.created_at >= cutoff_date
                    )
                )
                .group_by(Event.event_type)
                .all()
            )
            
            return {
                "total_events": total_events,
                "processed_events": processed_events,
                "pending_events": total_events - processed_events,
                "events_by_type": dict(events_by_type)
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de eventos: {e}")
            return {}
