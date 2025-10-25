from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class NotificationResult:
    """Resultado do envio de uma notificação"""
    
    def __init__(
        self,
        success: bool,
        message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        external_id: Optional[str] = None
    ):
        self.success = success
        self.message = message
        self.error_details = error_details
        self.external_id = external_id
        self.sent_at = datetime.utcnow() if success else None

class BaseNotificationChannel(ABC):
    """Interface base para canais de notificação"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    @abstractmethod
    async def send(
        self,
        recipient: str,
        title: str,
        message: str,
        channel_metadata: Optional[Dict[str, Any]] = None
    ) -> NotificationResult:
        """
        Envia uma notificação
        
        Args:
            recipient: Destinatário (email, telefone, webhook_url, etc.)
            title: Título da notificação
            message: Mensagem da notificação
            metadata: Metadados específicos do canal
        
        Returns:
            NotificationResult com o resultado do envio
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Valida a configuração do canal
        
        Args:
            config: Configuração do canal
        
        Returns:
            True se a configuração é válida
        """
        pass
    
    @abstractmethod
    def get_channel_name(self) -> str:
        """Retorna o nome do canal"""
        pass
    
    def _log_success(self, recipient: str, external_id: Optional[str] = None):
        """Log de sucesso"""
        self.logger.info(f"Notificação enviada com sucesso para {recipient}")
        if external_id:
            self.logger.info(f"ID externo: {external_id}")
    
    def _log_error(self, recipient: str, error: str, details: Optional[Dict[str, Any]] = None):
        """Log de erro"""
        self.logger.error(f"Erro ao enviar notificação para {recipient}: {error}")
        if details:
            self.logger.error(f"Detalhes do erro: {details}")
    
    def _create_error_result(self, error: str, details: Optional[Dict[str, Any]] = None) -> NotificationResult:
        """Cria um resultado de erro"""
        return NotificationResult(
            success=False,
            message=error,
            error_details=details
        )
    
    def _create_success_result(self, message: str = "Enviado com sucesso", external_id: Optional[str] = None) -> NotificationResult:
        """Cria um resultado de sucesso"""
        return NotificationResult(
            success=True,
            message=message,
            external_id=external_id
        )
