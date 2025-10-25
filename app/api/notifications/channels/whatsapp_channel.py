import aiohttp
import json
from typing import Dict, Any, Optional
import logging
from .base_channel import BaseNotificationChannel, NotificationResult

logger = logging.getLogger(__name__)

class WhatsAppChannel(BaseNotificationChannel):
    """Canal de notificação via WhatsApp (usando Twilio)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.account_sid = config.get('account_sid')
        self.auth_token = config.get('auth_token')
        self.from_number = config.get('from_number')  # Número do WhatsApp Business
        self.api_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        
        if not self.validate_config(config):
            raise ValueError("Configuração inválida para canal de WhatsApp")
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Valida a configuração do canal de WhatsApp"""
        required_fields = ['account_sid', 'auth_token', 'from_number']
        return all(field in config for field in required_fields)
    
    def get_channel_name(self) -> str:
        return "whatsapp"
    
    async def send(
        self,
        recipient: str,  # Número do WhatsApp (ex: +5511999999999)
        title: str,
        message: str,
        channel_metadata: Optional[Dict[str, Any]] = None
    ) -> NotificationResult:
        """Envia mensagem via WhatsApp"""
        try:
            # Prepara a mensagem
            full_message = f"*{title}*\n\n{message}"
            
            # Adiciona metadados se fornecidos
            if channel_metadata:
                full_message += f"\n\n_Dados adicionais:_\n"
                for key, value in channel_metadata.items():
                    full_message += f"• {key}: {value}\n"
            
            # Prepara os dados para a API do Twilio
            data = {
                'From': f"whatsapp:{self.from_number}",
                'To': f"whatsapp:{recipient}",
                'Body': full_message
            }
            
            # Envia a mensagem
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    data=data,
                    auth=aiohttp.BasicAuth(self.account_sid, self.auth_token),
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 201:
                        response_data = await response.json()
                        message_sid = response_data.get('sid')
                        self._log_success(recipient, message_sid)
                        return self._create_success_result(
                            "Mensagem WhatsApp enviada com sucesso",
                            external_id=message_sid
                        )
                    else:
                        error_data = await response.json()
                        error_msg = f"Erro ao enviar WhatsApp: {error_data.get('message', 'Erro desconhecido')}"
                        self._log_error(recipient, error_msg, error_data)
                        return self._create_error_result(error_msg, {
                            "status_code": response.status,
                            "twilio_error": error_data
                        })
                        
        except Exception as e:
            error_msg = f"Erro ao enviar WhatsApp: {str(e)}"
            self._log_error(recipient, error_msg)
            return self._create_error_result(error_msg, {"exception": str(e)})
