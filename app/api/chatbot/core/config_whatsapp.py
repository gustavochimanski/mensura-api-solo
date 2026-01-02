# app/api/chatbot/core/config_whatsapp.py
"""
Configuração da API do WhatsApp Business
"""

WHATSAPP_CONFIG = {
    "access_token": "EAAW5T51VWCEBQaMuT81F5kvl1T6c6WUvdfw9S8l5Wq2GV0mZApzX2In97Omt1Spwhiy0vJ8WOtP1VCJQXpgsPFTrXwG6ZCdWM80PrvZBOj2AQmNeGNbFcV95EsP8Pw2PGh2Ik77gkMpt40PnjTkRMP2c86QTdP2qzXUs4XCScPwsLx7t8ZB7RCBeZATE1wp26ZBa9gVkgCjPvlU6w4Uw0HmwTn8HzgLpyjLgj3nLpSXQ0kBmVmg7S2ZBcbfNyZCZBZCEY4DkBhbigZCmopGf6zqYyKC1WW69iZAeRIIOvAZDZD",
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
