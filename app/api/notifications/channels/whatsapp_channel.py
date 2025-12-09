import httpx
from typing import Dict, Any, Optional
import logging
from .base_channel import BaseNotificationChannel, NotificationResult

logger = logging.getLogger(__name__)

class WhatsAppChannel(BaseNotificationChannel):
    """Canal de notificação via WhatsApp Business API (Meta)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_token = config.get('access_token')
        self.phone_number_id = config.get('phone_number_id')
        self.api_version = config.get('api_version', 'v22.0')
        
        if not self.validate_config(config):
            raise ValueError("Configuração inválida para canal de WhatsApp")
        
        # Monta a URL da API do WhatsApp
        self.api_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Valida a configuração do canal de WhatsApp"""
        required_fields = ['access_token', 'phone_number_id']
        return all(field in config for field in required_fields)
    
    def get_channel_name(self) -> str:
        return "whatsapp"
    
    def _format_phone_number(self, phone: str) -> str:
        """
        Formata número de telefone para o formato do WhatsApp
        Remove caracteres especiais e garante que tenha o código do país
        """
        # Remove todos os caracteres não numéricos
        phone = ''.join(filter(str.isdigit, phone))
        
        # Se não começa com código do país, assume Brasil (55)
        if not phone.startswith('55'):
            phone = '55' + phone
        
        return phone
    
    def _get_headers(self) -> Dict[str, str]:
        """Retorna os headers para requisições à API do WhatsApp"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
    
    async def send(
        self,
        recipient: str,  # Número do WhatsApp (ex: +5511999999999 ou 11999999999)
        title: str,
        message: str,
        channel_metadata: Optional[Dict[str, Any]] = None
    ) -> NotificationResult:
        """Envia mensagem via WhatsApp Business API (Meta)"""
        try:
            # Formata o número para o padrão WhatsApp
            phone_formatted = self._format_phone_number(recipient)
            
            # Prepara a mensagem completa
            full_message = f"*{title}*\n\n{message}"
            
            # Adiciona metadados se fornecidos
            if channel_metadata:
                full_message += f"\n\n_Dados adicionais:_\n"
                for key, value in channel_metadata.items():
                    full_message += f"• {key}: {value}\n"
            
            # Payload da mensagem
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_formatted,
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": full_message
                }
            }
            
            # Headers com token de autorização
            headers = self._get_headers()
            
            # Envia a mensagem
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    message_id = result.get("messages", [{}])[0].get("id")
                    self._log_success(phone_formatted, message_id)
                    return self._create_success_result(
                        "Mensagem WhatsApp enviada com sucesso",
                        external_id=message_id
                    )
                else:
                    error_data = response.json() if response.text else {}
                    error_info = error_data.get("error", {})
                    error_msg = f"Erro ao enviar WhatsApp: {error_info.get('message', 'Erro desconhecido')}"
                    self._log_error(phone_formatted, error_msg, error_data)
                    return self._create_error_result(error_msg, {
                        "status_code": response.status_code,
                        "whatsapp_error": error_data,
                        "error_code": error_info.get("code"),
                        "error_type": error_info.get("type")
                    })
                        
        except Exception as e:
            error_msg = f"Erro ao enviar WhatsApp: {str(e)}"
            self._log_error(recipient, error_msg)
            return self._create_error_result(error_msg, {"exception": str(e)})
