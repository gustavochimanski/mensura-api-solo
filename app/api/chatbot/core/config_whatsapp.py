"""Configuração dinâmica da API do WhatsApp Business (agora vinda do banco)."""

from typing import Optional, Dict
from contextlib import contextmanager

from app.database.db_connection import SessionLocal
from app.api.notifications.repositories.whatsapp_config_repository import WhatsAppConfigRepository
from app.api.notifications.services.whatsapp_config_service import WhatsAppConfigService

# Fallback vazio para evitar segredos hardcoded
DEFAULT_WHATSAPP_CONFIG: Dict[str, str] = {
    "access_token": "",
    "phone_number_id": "",
    "business_account_id": "",
    "api_version": "v22.0",
    "send_mode": "api",
    "coexistence_enabled": False,
}


@contextmanager
def _service_ctx():
    db = SessionLocal()
    try:
        service = WhatsAppConfigService(WhatsAppConfigRepository(db))
        yield service
    finally:
        db.close()


def load_whatsapp_config(empresa_id: Optional[str] = None) -> Dict[str, str]:
    """
    Busca a configuração ativa no banco para a empresa informada.
    Se não houver, retorna o fallback vazio (DEFAULT_WHATSAPP_CONFIG).
    """
    with _service_ctx() as service:
        config = service.get_active_config(empresa_id) if empresa_id else None
        if config:
            return WhatsAppConfigService.to_response_dict(config)
    return DEFAULT_WHATSAPP_CONFIG.copy()


# Mantido por compatibilidade com códigos legados (evita erro de import)
WHATSAPP_CONFIG = load_whatsapp_config()


def get_whatsapp_url(empresa_id: Optional[str] = None, config: Optional[Dict[str, str]] = None) -> str:
    """Retorna a URL base da API do WhatsApp."""
    cfg = config or load_whatsapp_config(empresa_id)
    api_version = cfg.get("api_version", "v22.0")
    phone_number_id = cfg.get("phone_number_id")
    return f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"


def get_headers(empresa_id: Optional[str] = None, config: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Retorna os headers para requisições à API do WhatsApp."""
    cfg = config or load_whatsapp_config(empresa_id)
    access_token = cfg.get("access_token")
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def format_phone_number(phone: str) -> str:
    """
    Formata número de telefone para o formato do WhatsApp
    Remove caracteres especiais e garante que tenha o código do país
    """
    phone = ''.join(filter(str.isdigit, phone))
    if not phone.startswith('55'):
        phone = '55' + phone
    return phone
