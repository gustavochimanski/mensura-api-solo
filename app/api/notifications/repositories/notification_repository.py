from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from ..models.notification import Notification, NotificationLog, NotificationStatus, NotificationChannel, NotificationPriority
from ..schemas.notification_schemas import NotificationFilter

logger = logging.getLogger(__name__)

class NotificationRepository:
    """Repositório para operações com notificações"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, notification_data: Dict[str, Any]) -> Notification:
        """Cria uma nova notificação"""
        try:
            notification = Notification(**notification_data)
            self.db.add(notification)
            self.db.commit()
            self.db.refresh(notification)
            
            logger.info(f"Notificação criada: {notification.id}")
            return notification
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar notificação: {e}")
            raise
    
    def get_by_id(self, notification_id: str) -> Optional[Notification]:
        """Busca notificação por ID"""
        return self.db.query(Notification).filter(Notification.id == notification_id).first()
    
    def get_by_empresa(self, empresa_id: str, limit: int = 100, offset: int = 0) -> List[Notification]:
        """Busca notificações por empresa"""
        return (
            self.db.query(Notification)
            .filter(Notification.empresa_id == empresa_id)
            .order_by(desc(Notification.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
    
    def get_pending_notifications(self, limit: int = 100) -> List[Notification]:
        """Busca notificações pendentes para processamento"""
        return (
            self.db.query(Notification)
            .filter(
                and_(
                    Notification.status == NotificationStatus.PENDING,
                    or_(
                        Notification.next_retry_at.is_(None),
                        Notification.next_retry_at <= datetime.utcnow()
                    )
                )
            )
            .order_by(Notification.priority.desc(), Notification.created_at)
            .limit(limit)
            .all()
        )
    
    def get_failed_notifications(self, max_attempts: int = 3, limit: int = 100) -> List[Notification]:
        """Busca notificações que falharam e podem ser reprocessadas"""
        return (
            self.db.query(Notification)
            .filter(
                and_(
                    Notification.status == NotificationStatus.FAILED,
                    Notification.attempts < Notification.max_attempts,
                    or_(
                        Notification.next_retry_at.is_(None),
                        Notification.next_retry_at <= datetime.utcnow()
                    )
                )
            )
            .order_by(Notification.created_at)
            .limit(limit)
            .all()
        )
    
    def update_status(self, notification_id: str, status: NotificationStatus, 
                     attempts: Optional[int] = None, next_retry_at: Optional[datetime] = None) -> bool:
        """Atualiza status da notificação"""
        try:
            notification = self.get_by_id(notification_id)
            if not notification:
                return False
            
            notification.status = status
            notification.last_attempt_at = datetime.utcnow()
            
            if attempts is not None:
                notification.attempts = attempts
            
            if next_retry_at is not None:
                notification.next_retry_at = next_retry_at
            
            if status == NotificationStatus.SENT:
                notification.sent_at = datetime.utcnow()
            elif status == NotificationStatus.FAILED:
                notification.failed_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Status da notificação {notification_id} atualizado para {status}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar status da notificação {notification_id}: {e}")
            return False
    
    def increment_attempts(self, notification_id: str) -> bool:
        """Incrementa contador de tentativas"""
        try:
            notification = self.get_by_id(notification_id)
            if not notification:
                return False
            
            notification.attempts += 1
            notification.last_attempt_at = datetime.utcnow()
            
            # Calcula próxima tentativa (backoff exponencial)
            if notification.attempts < notification.max_attempts:
                delay_minutes = 2 ** notification.attempts  # 2, 4, 8 minutos
                notification.next_retry_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
                notification.status = NotificationStatus.RETRYING
            else:
                notification.status = NotificationStatus.FAILED
                notification.failed_at = datetime.utcnow()
            
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao incrementar tentativas da notificação {notification_id}: {e}")
            return False
    
    def add_log(self, notification_id: str, status: NotificationStatus, 
                message: Optional[str] = None, error_details: Optional[Dict[str, Any]] = None) -> bool:
        """Adiciona log à notificação"""
        try:
            log = NotificationLog(
                notification_id=notification_id,
                status=status,
                message=message,
                error_details=error_details
            )
            self.db.add(log)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao adicionar log à notificação {notification_id}: {e}")
            return False
    
    def get_logs(self, notification_id: str) -> List[NotificationLog]:
        """Busca logs de uma notificação"""
        return (
            self.db.query(NotificationLog)
            .filter(NotificationLog.notification_id == notification_id)
            .order_by(NotificationLog.created_at)
            .all()
        )
    
    def filter_notifications(self, filters: NotificationFilter, limit: int = 100, offset: int = 0) -> List[Notification]:
        """Filtra notificações com base nos critérios fornecidos"""
        query = self.db.query(Notification)
        
        if filters.empresa_id:
            query = query.filter(Notification.empresa_id == filters.empresa_id)
        
        if filters.user_id:
            query = query.filter(Notification.user_id == filters.user_id)
        
        if filters.event_type:
            query = query.filter(Notification.event_type == filters.event_type)
        
        if filters.channel:
            query = query.filter(Notification.channel == filters.channel)
        
        if filters.status:
            query = query.filter(Notification.status == filters.status)
        
        if filters.priority:
            query = query.filter(Notification.priority == filters.priority)
        
        if filters.created_from:
            query = query.filter(Notification.created_at >= filters.created_from)
        
        if filters.created_to:
            query = query.filter(Notification.created_at <= filters.created_to)
        
        return (
            query.order_by(desc(Notification.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
    
    def count_notifications(self, filters: NotificationFilter) -> int:
        """Conta notificações com base nos filtros"""
        query = self.db.query(Notification)
        
        if filters.empresa_id:
            query = query.filter(Notification.empresa_id == filters.empresa_id)
        
        if filters.user_id:
            query = query.filter(Notification.user_id == filters.user_id)
        
        if filters.event_type:
            query = query.filter(Notification.event_type == filters.event_type)
        
        if filters.channel:
            query = query.filter(Notification.channel == filters.channel)
        
        if filters.status:
            query = query.filter(Notification.status == filters.status)
        
        if filters.priority:
            query = query.filter(Notification.priority == filters.priority)
        
        if filters.created_from:
            query = query.filter(Notification.created_at >= filters.created_from)
        
        if filters.created_to:
            query = query.filter(Notification.created_at <= filters.created_to)
        
        return query.count()
    
    def delete_old_notifications(self, days: int = 30) -> int:
        """Remove notificações antigas"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        try:
            deleted_count = (
                self.db.query(Notification)
                .filter(
                    and_(
                        Notification.created_at < cutoff_date,
                        Notification.status.in_([NotificationStatus.SENT, NotificationStatus.CANCELLED])
                    )
                )
                .delete()
            )
            self.db.commit()
            logger.info(f"Removidas {deleted_count} notificações antigas")
            return deleted_count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao remover notificações antigas: {e}")
            return 0
