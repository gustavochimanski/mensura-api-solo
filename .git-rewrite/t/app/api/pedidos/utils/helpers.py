"""
Funções auxiliares para o bounded context de Pedidos.
"""
from __future__ import annotations

from typing import Any, Optional


def enum_value(enum_obj: Any) -> Optional[str]:
    """
    Extrai o valor de um enum como string.
    
    Args:
        enum_obj: Objeto enum ou valor string (pode ser None)
        
    Returns:
        String representando o valor do enum, ou None se enum_obj for None
    """
    if enum_obj is None:
        return None
    
    if hasattr(enum_obj, "value"):
        return enum_obj.value
    
    return str(enum_obj)

