# app/api/chatbot/core/config_whatsapp.py
"""
Configuração da API do WhatsApp Business
"""

WHATSAPP_CONFIG = {
    "access_token": "EAAW5T51VWCEBQTtRlPokM0QemXMKZB2ttdb1S7Bmwl6bAZCrlxOKpt3Kj90zaZAC7lSjTYoHuUfSlC1Wb9Xy6Sn0ic0ZAWUctfUdJruOIXmzqVZCnB6TqHhSeNAIS62zK6yZAev1msA0ieKtacZCyXeg0ptIEZBFA8Yl9QgQg4xQz8jnZB1kmTseaKUgnkVdlpnhK8vz3Vv46BIFjFxZAxii8BH1ZC84JZAYqmuZBmD7ZC5OVs7y1RTZBldENUFPFdLszMxnxQ1FokveNY4O9jOTesl7spIi8DrGrCEQ2aD7wZDZD",
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
