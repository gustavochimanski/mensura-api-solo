\"\"\"Adaptadores para reutilizar configurações e serviços existentes (legacy).\"\"\"
from typing import Any, Dict

try:
    # reutiliza a config legacy
    from app.api.chatbot.legacy.core.config_whatsapp import SOME_SETTING  # type: ignore
except Exception:
    SOME_SETTING = None

def get_config() -> Dict[str, Any]:
    return {\"some_setting\": SOME_SETTING}

