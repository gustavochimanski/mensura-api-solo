# app/api/chatbot/core/config_whatsapp.py
"""
Configuração da API do WhatsApp Business
"""

WHATSAPP_CONFIG = {
    "access_token": "EAAW5T51VWCEBQNoVY5OJZCqYNX0V9eCBKvqTu2kPanEZCBroaAHG4TMTDtwlRzbeTLKB5f5lyOZBRYwZAfcKgE3fiu05INg1ZBRmyMoXJ41AGS0jrFZAdSxIwymlFDadHspZATd8xIJx6qrp4B79ZBO9r6MxKlyAy1hO262BGcFJK10ivFXYm6ZCta0mbFZB3GdaRjBkZAua5FDKN2zZBjfbzdCiI5BiPYOuLggzxOZCE4xxZCPjFM10gwLVY3YpgZBexLcPBZAYhfw3tZCR6YLJPx7LVSrbBMBl9Ugi3r5DhnwZDZD",
    "phone_number_id": "887075554489957",
    "business_account_id": "1454221955671283",
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
