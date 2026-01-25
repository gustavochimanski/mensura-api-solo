"""Configuração dinâmica da API do WhatsApp Business (agora vinda do banco)."""

import os
from typing import Optional, Dict
from contextlib import contextmanager

from app.database.db_connection import SessionLocal
from app.api.notifications.repositories.whatsapp_config_repository import WhatsAppConfigRepository
from app.api.notifications.services.whatsapp_config_service import WhatsAppConfigService

# Configuração padrão agora usa 360dialog e evita credenciais hard-coded
D360_BASE_URL = os.getenv("D360_BASE_URL", "https://waba-v2.360dialog.io")
D360_API_KEY = os.getenv("D360_API_KEY", "")

# Fallback manual para 360dialog
DEFAULT_WHATSAPP_CONFIG: Dict[str, str] = {
    "access_token": D360_API_KEY,
    "d360_api_key": D360_API_KEY,
    "base_url": D360_BASE_URL,
    "provider": "360dialog",
    "phone_number_id": "",
    "business_account_id": "",
    "api_version": "v22.0",
    "webhook_url": "",
    "webhook_verify_token": "",
    "webhook_header_key": "",
    "webhook_header_value": "",
    "webhook_is_active": False,
    "webhook_status": "pending",
    "webhook_last_sync": None,
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
        # Busca ativo por empresa quando informado; caso contrário, usa fallback do service (último ativo)
        config = service.get_active_config(empresa_id)
        if config:
            cfg = WhatsAppConfigService.to_response_dict(config)
            # Garante base_url/provider mesmo se não estiverem no banco
            cfg.setdefault("base_url", D360_BASE_URL)
            cfg.setdefault("provider", "360dialog")
            cfg.setdefault("webhook_url", "")
            cfg.setdefault("webhook_verify_token", "")
            cfg.setdefault("webhook_header_key", "")
            cfg.setdefault("webhook_header_value", "")
            cfg.setdefault("webhook_is_active", False)
            cfg.setdefault("webhook_status", "pending")
            cfg.setdefault("webhook_last_sync", None)
            return cfg
    return DEFAULT_WHATSAPP_CONFIG.copy()


# Mantido por compatibilidade com códigos legados (evita erro de import).
# IMPORTANTE: não consultar o banco em import-time, porque isso força o SQLAlchemy
# a configurar os mappers cedo demais (antes de todos os models serem importados),
# podendo quebrar relações declaradas por string (ex.: "CaixaModel").
WHATSAPP_CONFIG = DEFAULT_WHATSAPP_CONFIG.copy()


def get_whatsapp_url(empresa_id: Optional[str] = None, config: Optional[Dict[str, str]] = None) -> str:
    """Retorna a URL base da API do WhatsApp."""
    cfg = config or load_whatsapp_config(empresa_id)
    base_url = cfg.get("base_url")
    provider = (cfg.get("provider") or "").lower()

    # Provedor primário: se provider estiver definido, ele manda.
    # Fallback: se provider vier vazio, inferimos pelo base_url (mantém compatibilidade).
    is_360 = (provider == "360dialog") or (not provider and "360dialog" in (base_url or "").lower())

    # 360dialog usa base_url dedicada sem phone_number_id
    if is_360:
        return f"{(base_url or D360_BASE_URL).rstrip('/')}/messages"

    api_version = cfg.get("api_version", "v22.0")
    phone_number_id = cfg.get("phone_number_id")
    return f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"


def get_headers(empresa_id: Optional[str] = None, config: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Retorna os headers para requisições à API do WhatsApp."""
    cfg = config or load_whatsapp_config(empresa_id)
    access_token = cfg.get("access_token") or ""
    base_url = cfg.get("base_url") or ""
    provider = (cfg.get("provider") or "").lower()

    # Valida se o token existe e não está vazio
    if not access_token or access_token.strip() == "":
        raise ValueError("Access token do WhatsApp não configurado ou vazio")

    # 360dialog: usa header D360-API-KEY
    is_360 = (provider == "360dialog") or (not provider and "360dialog" in base_url.lower())
    if is_360:
        return {
            "D360-API-KEY": access_token,
            "Content-Type": "application/json",
        }

    # Fallback Meta Cloud API
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def format_phone_number(phone: str) -> str:
    """
    Formata número de telefone para o formato do WhatsApp
    Remove caracteres especiais e garante que tenha o código do país
    
    IMPORTANTE: Usa o número EXATAMENTE como recebido, sem adicionar dígitos como "9"
    """
    phone = ''.join(filter(str.isdigit, phone))
    if not phone.startswith('55'):
        phone = '55' + phone
    return phone
