from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..models.subscription import NotificationSubscription
from ..schemas.subscription_schemas import SubscriptionFilter

logger = logging.getLogger(__name__)

class SubscriptionRepository:
    """Repositório para operações com assinaturas de notificação"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, subscription_data: Dict[str, Any]) -> NotificationSubscription:
        """Cria uma nova assinatura"""
        try:
            subscription = NotificationSubscription(**subscription_data)
            self.db.add(subscription)
            self.db.commit()
            self.db.refresh(subscription)
            
            logger.info(f"Assinatura criada: {subscription.id}")
            return subscription
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar assinatura: {e}")
            raise
    
    def get_by_id(self, subscription_id: str) -> Optional[NotificationSubscription]:
        """Busca assinatura por ID"""
        return self.db.query(NotificationSubscription).filter(NotificationSubscription.id == subscription_id).first()
    
    def get_by_empresa(self, empresa_id: str, limit: int = 100, offset: int = 0) -> List[NotificationSubscription]:
        """Busca assinaturas por empresa"""
        return (
            self.db.query(NotificationSubscription)
            .filter(NotificationSubscription.empresa_id == empresa_id)
            .order_by(desc(NotificationSubscription.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
    
    def get_active_subscriptions(self, empresa_id: str, event_type: str) -> List[NotificationSubscription]:
        """Busca assinaturas ativas para um evento específico"""
        return (
            self.db.query(NotificationSubscription)
            .filter(
                and_(
                    NotificationSubscription.empresa_id == empresa_id,
                    NotificationSubscription.event_type == event_type,
                    NotificationSubscription.active == True
                )
            )
            .all()
        )
    
    def get_user_subscriptions(self, user_id: str, limit: int = 100, offset: int = 0) -> List[NotificationSubscription]:
        """Busca assinaturas de um usuário"""
        return (
            self.db.query(NotificationSubscription)
            .filter(NotificationSubscription.user_id == user_id)
            .order_by(desc(NotificationSubscription.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
    
    def update(self, subscription_id: str, update_data: Dict[str, Any]) -> bool:
        """Atualiza uma assinatura"""
        try:
            subscription = self.get_by_id(subscription_id)
            if not subscription:
                return False
            
            for key, value in update_data.items():
                if hasattr(subscription, key):
                    setattr(subscription, key, value)
            
            subscription.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Assinatura {subscription_id} atualizada")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar assinatura {subscription_id}: {e}")
            return False
    
    def delete(self, subscription_id: str) -> bool:
        """Remove uma assinatura"""
        try:
            subscription = self.get_by_id(subscription_id)
            if not subscription:
                return False
            
            self.db.delete(subscription)
            self.db.commit()
            
            logger.info(f"Assinatura {subscription_id} removida")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao remover assinatura {subscription_id}: {e}")
            return False
    
    def toggle_active(self, subscription_id: str) -> bool:
        """Ativa/desativa uma assinatura"""
        try:
            subscription = self.get_by_id(subscription_id)
            if not subscription:
                return False
            
            subscription.active = not subscription.active
            subscription.updated_at = datetime.utcnow()
            self.db.commit()
            
            status = "ativada" if subscription.active else "desativada"
            logger.info(f"Assinatura {subscription_id} {status}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao alterar status da assinatura {subscription_id}: {e}")
            return False
    
    def filter_subscriptions(self, filters: SubscriptionFilter, limit: int = 100, offset: int = 0) -> List[NotificationSubscription]:
        """Filtra assinaturas com base nos critérios fornecidos"""
        query = self.db.query(NotificationSubscription)
        
        if filters.empresa_id:
            query = query.filter(NotificationSubscription.empresa_id == filters.empresa_id)
        
        if filters.user_id:
            query = query.filter(NotificationSubscription.user_id == filters.user_id)
        
        if filters.event_type:
            query = query.filter(NotificationSubscription.event_type == filters.event_type)
        
        if filters.channel:
            query = query.filter(NotificationSubscription.channel == filters.channel)
        
        if filters.active is not None:
            query = query.filter(NotificationSubscription.active == filters.active)
        
        return (
            query.order_by(desc(NotificationSubscription.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
    
    def count_subscriptions(self, filters: SubscriptionFilter) -> int:
        """Conta assinaturas com base nos filtros"""
        query = self.db.query(NotificationSubscription)
        
        if filters.empresa_id:
            query = query.filter(NotificationSubscription.empresa_id == filters.empresa_id)
        
        if filters.user_id:
            query = query.filter(NotificationSubscription.user_id == filters.user_id)
        
        if filters.event_type:
            query = query.filter(NotificationSubscription.event_type == filters.event_type)
        
        if filters.channel:
            query = query.filter(NotificationSubscription.channel == filters.channel)
        
        if filters.active is not None:
            query = query.filter(NotificationSubscription.active == filters.active)
        
        return query.count()
    
    def get_subscriptions_by_channel(self, empresa_id: str, channel: str) -> List[NotificationSubscription]:
        """Busca assinaturas por canal"""
        return (
            self.db.query(NotificationSubscription)
            .filter(
                and_(
                    NotificationSubscription.empresa_id == empresa_id,
                    NotificationSubscription.channel == channel,
                    NotificationSubscription.active == True
                )
            )
            .all()
        )
    
    def get_subscription_statistics(self, empresa_id: str) -> Dict[str, Any]:
        """Retorna estatísticas de assinaturas"""
        try:
            # Total de assinaturas
            total_subscriptions = (
                self.db.query(NotificationSubscription)
                .filter(NotificationSubscription.empresa_id == empresa_id)
                .count()
            )
            
            # Assinaturas ativas
            active_subscriptions = (
                self.db.query(NotificationSubscription)
                .filter(
                    and_(
                        NotificationSubscription.empresa_id == empresa_id,
                        NotificationSubscription.active == True
                    )
                )
                .count()
            )
            
            # Assinaturas por canal
            subscriptions_by_channel = (
                self.db.query(NotificationSubscription.channel, func.count(NotificationSubscription.id))
                .filter(NotificationSubscription.empresa_id == empresa_id)
                .group_by(NotificationSubscription.channel)
                .all()
            )
            
            # Assinaturas por tipo de evento
            subscriptions_by_event = (
                self.db.query(NotificationSubscription.event_type, func.count(NotificationSubscription.id))
                .filter(NotificationSubscription.empresa_id == empresa_id)
                .group_by(NotificationSubscription.event_type)
                .all()
            )
            
            return {
                "total_subscriptions": total_subscriptions,
                "active_subscriptions": active_subscriptions,
                "inactive_subscriptions": total_subscriptions - active_subscriptions,
                "subscriptions_by_channel": dict(subscriptions_by_channel),
                "subscriptions_by_event": dict(subscriptions_by_event)
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de assinaturas: {e}")
            return {}
