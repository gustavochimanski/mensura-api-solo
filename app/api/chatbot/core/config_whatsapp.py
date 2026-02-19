"""
Compat shim para configuração do WhatsApp usada por adaptadores de notification.

Fornece:
- load_whatsapp_config(empresa_id) -> dict com possíveis chaves:
  'access_token', 'phone_number_id', 'api_version', 'provider', 'base_url'
- format_phone_number(phone) -> str (normaliza para envio/registro)

Implementação mínima: tenta ler variáveis de ambiente específicas por empresa,
devolve {} se nada for encontrado. Usa utilitário existente para normalizar telefone.
"""
import os
from typing import Dict, Any, Optional

def load_whatsapp_config(empresa_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Carrega configuração do WhatsApp a partir de variáveis de ambiente (fallback).
    Variáveis suportadas (por precedência):
      - WHATSAPP_ACCESS_TOKEN_{EMPRESA_ID} / WHATSAPP_ACCESS_TOKEN
      - WHATSAPP_PHONE_NUMBER_ID_{EMPRESA_ID} / WHATSAPP_PHONE_NUMBER_ID
      - WHATSAPP_API_VERSION (opcional, default 'v22.0')
      - WHATSAPP_PROVIDER (opcional, ex: '360dialog')
      - WHATSAPP_BASE_URL (opcional)
    """
    suffix = f"_{empresa_id}" if empresa_id is not None else ""
    access_token = os.getenv(f"WHATSAPP_ACCESS_TOKEN{suffix}") or os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.getenv(f"WHATSAPP_PHONE_NUMBER_ID{suffix}") or os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    api_version = os.getenv("WHATSAPP_API_VERSION", "v22.0")
    provider = os.getenv("WHATSAPP_PROVIDER", "360dialog")
    base_url = os.getenv("WHATSAPP_BASE_URL", "https://waba-v2.360dialog.io")

    config: Dict[str, Any] = {}
    if access_token:
        config["access_token"] = access_token
    if phone_number_id:
        config["phone_number_id"] = phone_number_id
    if api_version:
        config["api_version"] = api_version
    if provider:
        config["provider"] = provider
    if base_url:
        config["base_url"] = base_url
    return config


def format_phone_number(phone: str) -> str:
    """
    Normaliza telefone para formato de armazenamento/consulta/whatsapp.
    Usa utilitário do projeto quando disponível; caso contrário, faz limpeza básica.
    """
    try:
        from app.utils.telefone import normalizar_telefone_para_armazenar
        normalized = normalizar_telefone_para_armazenar(phone)
        return normalized or str(phone).strip()
    except Exception:
        # Fallback mínimo: remove tudo que não for dígito e retorna
        digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
        return digits

