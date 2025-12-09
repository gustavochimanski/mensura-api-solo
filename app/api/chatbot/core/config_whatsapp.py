# app/api/chatbot/core/config_whatsapp.py
"""
Configuração da API do WhatsApp Business
"""

WHATSAPP_CONFIG = {
    "access_token": "EAAWrQRyXUaoBQGCMKVuTSISx14O1DOZBZB5w1JVZBZC2k1Ak3s90g693NZCgVZC0XUWUfcsiHy6soE1wx9vUj4ZCfBWJRUp1iLZBJD4QlrlAT9rR346YYE36b2tt2L3NUOnfYZBsW0faNsbokoFBvTwML6EV3Gvqs6asSI0vR962scFR24unyTFQ6Vaykvhlmku0LKynLwQP9sEdnY7fxIpfKIRsUHj9It4d08zWX",
    "phone_number_id": "865697123299398",
    "business_account_id": "61584706713620",
    "api_version": "v22.0",
    "send_mode": "api"
}


def get_whatsapp_url():
    """Retorna a URL base da API do WhatsApp"""
    api_version = WHATSAPP_CONFIG.get("api_version", "v22.0")
    phone_number_id = WHATSAPP_CONFIG.get("phone_number_id")
    return f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"


def get_headers():
    """Retorna os headers para requisições à API do WhatsApp"""
    access_token = WHATSAPP_CONFIG.get("access_token")
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def format_phone_number(phone: str) -> str:
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
