"""Contrato para provedor de destinatários"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class IRecipientProvider(ABC):
    """Interface para provedor de destinatários de notificações"""
    
    @abstractmethod
    def get_recipient_by_id(self, recipient_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca informações de um destinatário por ID
        
        Args:
            recipient_id: ID do destinatário (pode ser user_id, cliente_id, etc)
            
        Returns:
            Dicionário com informações do destinatário (email, phone, user_id) ou None
        """
        pass
    
    @abstractmethod
    def get_recipients_by_ids(self, recipient_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Busca informações de múltiplos destinatários por IDs
        
        Args:
            recipient_ids: Lista de IDs dos destinatários
            
        Returns:
            Lista de dicionários com informações dos destinatários
        """
        pass
    
    @abstractmethod
    def get_recipients_by_filters(
        self,
        empresa_id: str,
        filter_by_empresa: bool = True,
        filter_by_user_type: Optional[str] = None,
        filter_by_tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca destinatários baseado em filtros
        
        Args:
            empresa_id: ID da empresa
            filter_by_empresa: Se True, busca todos os destinatários da empresa
            filter_by_user_type: Filtrar por tipo de usuário (opcional)
            filter_by_tags: Filtrar por tags (opcional)
            
        Returns:
            Lista de destinatários com suas informações (email, phone, user_id)
        """
        pass

