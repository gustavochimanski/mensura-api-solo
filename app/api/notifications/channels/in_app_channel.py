from typing import Dict, Any, Optional
import logging
from .base_channel import BaseNotificationChannel, NotificationResult

logger = logging.getLogger(__name__)

class InAppChannel(BaseNotificationChannel):
    """Canal de notificação in-app (WebSocket/SSE)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.websocket_manager = config.get('websocket_manager')
        
        if not self.validate_config(config):
            raise ValueError("Configuração inválida para canal in-app")
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Valida a configuração do canal in-app"""
        return 'websocket_manager' in config
    
    def get_channel_name(self) -> str:
        return "in_app"
    
    async def send(
        self,
        recipient: str,  # user_id ou session_id
        title: str,
        message: str,
        channel_metadata: Optional[Dict[str, Any]] = None
    ) -> NotificationResult:
        """Envia notificação in-app via WebSocket"""
        try:
            if not self.websocket_manager:
                return self._create_error_result("WebSocket manager não configurado")
            
            # Prepara os dados da notificação
            notification_data = {
                "type": "notification",
                "title": title,
                "message": message,
                "channel_metadata": channel_metadata or {},
                "timestamp": self._get_timestamp()
            }
            
            # Envia via WebSocket
            success = await self.websocket_manager.send_to_user(recipient, notification_data)
            
            if success:
                self._log_success(recipient)
                return self._create_success_result("Notificação in-app enviada com sucesso")
            else:
                error_msg = "Usuário não conectado ou erro no WebSocket"
                self._log_error(recipient, error_msg)
                return self._create_error_result(error_msg)
                
        except Exception as e:
            error_msg = f"Erro ao enviar notificação in-app: {str(e)}"
            self._log_error(recipient, error_msg)
            return self._create_error_result(error_msg, {"exception": str(e)})
    
    def _get_timestamp(self) -> str:
        """Retorna timestamp atual em formato ISO"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
