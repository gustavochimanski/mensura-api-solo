"""Contrato para o serviço de disparo de mensagens"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from ..schemas.message_dispatch_schemas import (
    DispatchMessageRequest,
    DispatchMessageResponse,
    BulkDispatchRequest
)
from ..models.notification import MessageType

class IMessageDispatchService(ABC):
    """Interface para o serviço de disparo de mensagens"""
    
    @abstractmethod
    async def dispatch_message(self, request: DispatchMessageRequest) -> DispatchMessageResponse:
        """
        Dispara uma mensagem para um ou mais destinatários através de múltiplos canais
        
        Args:
            request: Dados do disparo de mensagem
            
        Returns:
            Resposta com informações sobre o disparo
        """
        pass
    
    @abstractmethod
    async def bulk_dispatch(self, request: BulkDispatchRequest) -> DispatchMessageResponse:
        """
        Dispara mensagem em massa baseado em filtros
        
        Args:
            request: Dados do disparo em massa
            
        Returns:
            Resposta com informações sobre o disparo
        """
        pass
    
    @abstractmethod
    def get_dispatch_stats(
        self,
        empresa_id: str,
        message_type: Optional[MessageType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Obtém estatísticas de disparos de mensagens
        
        Args:
            empresa_id: ID da empresa
            message_type: Tipo de mensagem (opcional)
            start_date: Data inicial (opcional)
            end_date: Data final (opcional)
            
        Returns:
            Dicionário com estatísticas
        """
        pass

