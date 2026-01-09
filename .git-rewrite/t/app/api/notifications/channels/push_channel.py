import aiohttp
import json
from typing import Dict, Any, Optional
import logging
from .base_channel import BaseNotificationChannel, NotificationResult

logger = logging.getLogger(__name__)

class PushChannel(BaseNotificationChannel):
    """Canal de notificação push (usando Firebase Cloud Messaging)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.server_key = config.get('server_key')
        self.fcm_url = "https://fcm.googleapis.com/fcm/send"
        
        if not self.validate_config(config):
            raise ValueError("Configuração inválida para canal de push")
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Valida a configuração do canal de push"""
        return 'server_key' in config and config['server_key']
    
    def get_channel_name(self) -> str:
        return "push"
    
    async def send(
        self,
        recipient: str,  # Device token do Firebase
        title: str,
        message: str,
        channel_metadata: Optional[Dict[str, Any]] = None
    ) -> NotificationResult:
        """Envia notificação push"""
        try:
            # Prepara o payload da notificação
            notification_payload = {
                "to": recipient,
                "notification": {
                    "title": title,
                    "body": message,
                    "sound": "default",
                    "badge": 1
                },
                "data": channel_metadata or {},
                "priority": "high"
            }
            
            # Headers para FCM
            headers = {
                "Authorization": f"key={self.server_key}",
                "Content-Type": "application/json"
            }
            
            # Envia a notificação
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.fcm_url,
                    json=notification_payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        message_id = response_data.get('message_id')
                        self._log_success(recipient, message_id)
                        return self._create_success_result(
                            "Notificação push enviada com sucesso",
                            external_id=message_id
                        )
                    else:
                        error_data = await response.json()
                        error_msg = f"Erro ao enviar push: {error_data.get('error', 'Erro desconhecido')}"
                        self._log_error(recipient, error_msg, error_data)
                        return self._create_error_result(error_msg, {
                            "status_code": response.status,
                            "fcm_error": error_data
                        })
                        
        except Exception as e:
            error_msg = f"Erro ao enviar push: {str(e)}"
            self._log_error(recipient, error_msg)
            return self._create_error_result(error_msg, {"exception": str(e)})
