# app/api/chatbot/core/config_whatsapp.py
"""
Configuração da API do WhatsApp Business
"""

WHATSAPP_CONFIG = {
    "access_token": "EAAWrQRyXUaoBQGUm0oFmheVu6RIFTvEMv3Nce1f89jKitCqDaTxe1XFZBl0ZBeQGXqtaUye4ZBOLs3eknDCjKTY30sqYY3QaiOv4KJZAnaAXTJ71fTXcVGsJuFwb7shTaw7XPZCD6lTh5tKmwqrJZBZAYZAt1ZBcJOlLmWrIPG25SWZApYw2Yi4Ybg217aZBmrcfTrbZAPiOYYf1lYWd4NuCYx2ZBMlQU5yGarszBZBFD0mqAFY6WZAEIWdRFZA79xN13EBBznoQZCNZBa95ukjZCCTVptd2SOO",
    "phone_number_id": "865697123299398",
    "business_account_id": "1435285257954191",
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
