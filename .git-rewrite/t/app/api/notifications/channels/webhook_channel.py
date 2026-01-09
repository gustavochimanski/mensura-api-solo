import aiohttp
import json
from typing import Dict, Any, Optional
import logging
from .base_channel import BaseNotificationChannel, NotificationResult

logger = logging.getLogger(__name__)

class WebhookChannel(BaseNotificationChannel):
    """Canal de notificação via webhook"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config.get('webhook_url')
        self.timeout = config.get('timeout', 30)
        self.headers = config.get('headers', {})
        self.auth_type = config.get('auth_type', 'none')  # none, bearer, basic
        self.auth_token = config.get('auth_token')
        self.username = config.get('username')
        self.password = config.get('password')
        
        if not self.validate_config(config):
            raise ValueError("Configuração inválida para canal de webhook")
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Valida a configuração do canal de webhook"""
        return 'webhook_url' in config and config['webhook_url']
    
    def get_channel_name(self) -> str:
        return "webhook"
    
    async def send(
        self,
        recipient: str,  # Neste caso, recipient é o webhook_url
        title: str,
        message: str,
        channel_metadata: Optional[Dict[str, Any]] = None
    ) -> NotificationResult:
        """Envia notificação via webhook"""
        try:
            # Prepara os dados do webhook
            webhook_data = {
                "title": title,
                "message": message,
                "timestamp": self._get_timestamp(),
                "channel_metadata": channel_metadata or {}
            }
            
            # Prepara headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mensura-Notification-Service/1.0",
                **self.headers
            }
            
            # Adiciona autenticação se configurada
            if self.auth_type == 'bearer' and self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            elif self.auth_type == 'basic' and self.username and self.password:
                import base64
                credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"
            
            # Envia o webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    recipient,
                    json=webhook_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status >= 200 and response.status < 300:
                        response_data = await response.json() if response.content_type == 'application/json' else None
                        self._log_success(recipient, f"Status: {response.status}")
                        return self._create_success_result(
                            f"Webhook enviado com sucesso (Status: {response.status})",
                            external_id=response_data.get('id') if response_data else None
                        )
                    else:
                        error_msg = f"Webhook retornou status {response.status}"
                        response_text = await response.text()
                        self._log_error(recipient, error_msg, {"response": response_text})
                        return self._create_error_result(error_msg, {
                            "status_code": response.status,
                            "response": response_text
                        })
                        
        except aiohttp.ClientTimeout:
            error_msg = f"Timeout ao enviar webhook para {recipient}"
            self._log_error(recipient, error_msg)
            return self._create_error_result(error_msg, {"timeout": self.timeout})
            
        except Exception as e:
            error_msg = f"Erro ao enviar webhook: {str(e)}"
            self._log_error(recipient, error_msg)
            return self._create_error_result(error_msg, {"exception": str(e)})
    
    def _get_timestamp(self) -> str:
        """Retorna timestamp atual em formato ISO"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
