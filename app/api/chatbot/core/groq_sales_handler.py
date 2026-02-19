"""Stub implementation for groq_sales_handler used during migration.
This provides minimal constants and functions so the router can import
the names without failing. Replace with real implementation when available.
"""
from app.config.settings import MODEL_NAME, GROQ_API_URL, GROQ_API_KEY, STATE_CADASTRO_NOME

class GroqSalesHandler:
    def __init__(self, *args, **kwargs):
        pass

def processar_mensagem_groq(*args, **kwargs):
    # Minimal placeholder: return a dict indicating unimplemented.
    return {"ok": False, "reason": "groq handler not implemented"}

__all__ = ["MODEL_NAME", "GROQ_API_URL", "GROQ_API_KEY", "GroqSalesHandler", "processar_mensagem_groq", "STATE_CADASTRO_NOME"]

