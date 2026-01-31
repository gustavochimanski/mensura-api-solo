import httpx
from typing import Dict, Any, Optional
import logging
from .base_channel import BaseNotificationChannel, NotificationResult
from ..services.notification_message_contract_default import DefaultNotificationMessageContract

logger = logging.getLogger(__name__)


class WhatsAppChannel(BaseNotificationChannel):
    """Canal de notificação via WhatsApp (agora usando 360dialog por padrão)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_token = config.get("access_token")
        self.phone_number_id = config.get("phone_number_id")
        self.api_version = config.get("api_version", "v22.0")
        self.base_url = config.get("base_url", "https://waba-v2.360dialog.io")
        self.provider = config.get("provider", "360dialog")
        provider_norm = (self.provider or "").lower()
        base_url_norm = (self.base_url or "").lower()
        # `provider` tem precedência. Se estiver vazio, inferimos pelo base_url (compatibilidade).
        self.is_360 = (provider_norm == "360dialog") or (not provider_norm and "360dialog" in base_url_norm)
        
        if not self.validate_config(config):
            raise ValueError("Configuração inválida para canal de WhatsApp")
        
        # Monta a URL da API conforme o provedor
        if self.is_360:
            # 360dialog (WABA v2): endpoint padrão é /messages (sem /v1)
            self.api_url = f"{self.base_url.rstrip('/')}/messages"
        else:
            self.api_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Valida a configuração do canal de WhatsApp"""
        provider_norm = (config.get("provider") or "").lower()
        base_url_norm = str(config.get("base_url", "") or "").lower()
        is_360 = (provider_norm == "360dialog") or (not provider_norm and "360dialog" in base_url_norm)
        if is_360:
            return bool(config.get("access_token"))
        required_fields = ["access_token", "phone_number_id"]
        return all(field in config for field in required_fields)
    
    def get_channel_name(self) -> str:
        return "whatsapp"
    
    def _format_phone_number(self, phone: str) -> str:
        """
        Formata número de telefone para o formato do WhatsApp
        Remove caracteres especiais e garante que tenha o código do país
        """
        # Unificação BR: garante 55 + DDD + 9 dígitos (quando parecer celular)
        from app.utils.telefone import normalizar_telefone_para_armazenar

        return normalizar_telefone_para_armazenar(phone) or ""
    
    def _get_headers(self) -> Dict[str, str]:
        """Retorna os headers para requisições à API do WhatsApp"""
        if self.is_360:
            return {
                "D360-API-KEY": self.access_token,
                "Content-Type": "application/json",
            }
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
        """Envia mensagem via WhatsApp (360dialog ou Meta Cloud API)"""
        try:
            # Formata o número para o padrão WhatsApp
            phone_formatted = self._format_phone_number(recipient)

            # Contract de mensagem: permite template (necessário sem interação/janela 24h)
            contract = DefaultNotificationMessageContract()
            payload = contract.build_whatsapp_payload(
                recipient_phone=phone_formatted,
                title=title,
                message=message,
                is_360=self.is_360,
                channel_metadata=channel_metadata,
            )
            
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
                    error_info = error_data.get("error", {}) if isinstance(error_data, dict) else {}
                    error_msg = error_info.get("message", "Erro ao enviar WhatsApp")
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
