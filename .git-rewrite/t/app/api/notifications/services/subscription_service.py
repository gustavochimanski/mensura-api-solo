from typing import List, Optional, Dict, Any
import logging

from ..repositories.subscription_repository import SubscriptionRepository
from ..schemas.subscription_schemas import (
    CreateSubscriptionRequest,
    UpdateSubscriptionRequest,
    SubscriptionFilter
)
from ..channels.channel_factory import ChannelFactory

logger = logging.getLogger(__name__)

class SubscriptionService:
    """Serviço para gerenciar assinaturas de notificação"""
    
    def __init__(self, subscription_repo: SubscriptionRepository):
        self.subscription_repo = subscription_repo
        self.channel_factory = ChannelFactory()
    
    def create_subscription(self, request: CreateSubscriptionRequest) -> str:
        """Cria uma nova assinatura"""
        try:
            # Valida configuração do canal
            if not self._validate_channel_config(request.channel, request.channel_config):
                raise ValueError(f"Configuração inválida para canal {request.channel}")
            
            subscription_data = {
                "empresa_id": request.empresa_id,
                "user_id": request.user_id,
                "event_type": request.event_type,
                "channel": request.channel,
                "channel_config": request.channel_config,
                "active": request.active,
                "filters": request.filters
            }
            
            subscription = self.subscription_repo.create(subscription_data)
            logger.info(f"Assinatura criada: {subscription.id}")
            return subscription.id
            
        except Exception as e:
            logger.error(f"Erro ao criar assinatura: {e}")
            raise
    
    def update_subscription(self, subscription_id: str, request: UpdateSubscriptionRequest) -> bool:
        """Atualiza uma assinatura"""
        try:
            subscription = self.subscription_repo.get_by_id(subscription_id)
            if not subscription:
                logger.warning(f"Assinatura {subscription_id} não encontrada")
                return False
            
            update_data = {}
            
            if request.channel_config is not None:
                # Valida nova configuração do canal
                if not self._validate_channel_config(subscription.channel, request.channel_config):
                    raise ValueError(f"Configuração inválida para canal {subscription.channel}")
                update_data["channel_config"] = request.channel_config
            
            if request.active is not None:
                update_data["active"] = request.active
            
            if request.filters is not None:
                update_data["filters"] = request.filters
            
            if update_data:
                success = self.subscription_repo.update(subscription_id, update_data)
                if success:
                    logger.info(f"Assinatura {subscription_id} atualizada")
                return success
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar assinatura {subscription_id}: {e}")
            raise
    
    def delete_subscription(self, subscription_id: str) -> bool:
        """Remove uma assinatura"""
        try:
            success = self.subscription_repo.delete(subscription_id)
            if success:
                logger.info(f"Assinatura {subscription_id} removida")
            return success
        except Exception as e:
            logger.error(f"Erro ao remover assinatura {subscription_id}: {e}")
            raise
    
    def toggle_subscription(self, subscription_id: str) -> bool:
        """Ativa/desativa uma assinatura"""
        try:
            success = self.subscription_repo.toggle_active(subscription_id)
            if success:
                subscription = self.subscription_repo.get_by_id(subscription_id)
                status = "ativada" if subscription.active else "desativada"
                logger.info(f"Assinatura {subscription_id} {status}")
            return success
        except Exception as e:
            logger.error(f"Erro ao alterar status da assinatura {subscription_id}: {e}")
            raise
    
    def get_subscription_by_id(self, subscription_id: str):
        """Busca assinatura por ID"""
        return self.subscription_repo.get_by_id(subscription_id)
    
    def get_subscriptions_by_empresa(self, empresa_id: str, limit: int = 100, offset: int = 0):
        """Busca assinaturas por empresa"""
        return self.subscription_repo.get_by_empresa(empresa_id, limit, offset)
    
    def get_user_subscriptions(self, user_id: str, limit: int = 100, offset: int = 0):
        """Busca assinaturas de um usuário"""
        return self.subscription_repo.get_user_subscriptions(user_id, limit, offset)
    
    def get_active_subscriptions(self, empresa_id: str, event_type: str):
        """Busca assinaturas ativas para um evento"""
        return self.subscription_repo.get_active_subscriptions(empresa_id, event_type)
    
    def filter_subscriptions(self, filters: SubscriptionFilter, limit: int = 100, offset: int = 0):
        """Filtra assinaturas"""
        return self.subscription_repo.filter_subscriptions(filters, limit, offset)
    
    def count_subscriptions(self, filters: SubscriptionFilter) -> int:
        """Conta assinaturas com base nos filtros"""
        return self.subscription_repo.count_subscriptions(filters)
    
    def get_subscription_statistics(self, empresa_id: str) -> Dict[str, Any]:
        """Retorna estatísticas de assinaturas"""
        return self.subscription_repo.get_subscription_statistics(empresa_id)
    
    def _validate_channel_config(self, channel: str, config: Dict[str, Any]) -> bool:
        """Valida configuração do canal"""
        try:
            return self.channel_factory.validate_channel_config(channel, config)
        except Exception as e:
            logger.error(f"Erro ao validar configuração do canal {channel}: {e}")
            return False
    
    def get_supported_channels(self) -> List[str]:
        """Retorna lista de canais suportados"""
        return self.channel_factory.get_supported_channels()
    
    def test_channel_config(self, channel: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Testa configuração de um canal"""
        try:
            if not self._validate_channel_config(channel, config):
                return {
                    "success": False,
                    "message": "Configuração inválida",
                    "errors": ["Campos obrigatórios não fornecidos ou inválidos"]
                }
            
            # Aqui você poderia implementar testes reais dos canais
            # Por exemplo, testar conexão SMTP, webhook, etc.
            return {
                "success": True,
                "message": "Configuração válida",
                "channel": channel
            }
            
        except Exception as e:
            logger.error(f"Erro ao testar configuração do canal {channel}: {e}")
            return {
                "success": False,
                "message": f"Erro ao testar canal: {str(e)}",
                "errors": [str(e)]
            }
