# app/api/chatbot/core/config_whatsapp.py
"""
Configuração da API do WhatsApp Business
"""

WHATSAPP_CONFIG = {
    "access_token": "EAAWrQRyXUaoBQAmiLqZBsgU5UCUOoehAAOBdFz5raAMxwJVvy62FdYgJZCJzbdy4J7ma3jTcRjE4w6jeNFzMMCRopjaHO0ITxB5P8oxaWiTWSoTco8tjqGSS48zEy9aS0Ud9QDxsxehCQCEs2QucHlPqTPSU5pANQ1L6nZBauvJZC0TblcxHj9OZClKOpNPjCnn0eyYjYQCvzw5VZA8pEM9gZBYmNHm0WbsbwQSB9lHlSQsSyvBUS1PqHV8lqxEMLOKIdiWy3zhM3D8K5fwjxhU",
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
