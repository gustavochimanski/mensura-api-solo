"""
Módulo de infraestrutura compartilhada do banco de dados.
Responsável por configurações globais que não pertencem a um domínio específico.
"""

from .postgis import habilitar_postgis
from .timezone import configurar_timezone
from .schemas import criar_schemas, SCHEMAS
from .enums import criar_enums

__all__ = [
    "habilitar_postgis",
    "configurar_timezone",
    "criar_schemas",
    "criar_enums",
    "SCHEMAS",
]

