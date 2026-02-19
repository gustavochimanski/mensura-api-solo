\"\"\"Adaptadores para reutilizar configurações e serviços existentes (legacy).\"\"\"
from typing import Any, Dict

try:
    # reutiliza a config legacy via import relativo
    from ..legacy.core import config_whatsapp as config_whatsapp  # type: ignore
    SOME_SETTING = getattr(config_whatsapp, \"SOME_SETTING\", None)
except Exception:
    SOME_SETTING = None

def get_config() -> Dict[str, Any]:
    return {\"some_setting\": SOME_SETTING}

