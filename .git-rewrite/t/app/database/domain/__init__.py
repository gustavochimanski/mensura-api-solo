"""
Sistema de domínios para inicialização do banco de dados.
"""

from .registry import DomainRegistry, register_domain
from .base import DomainInitializer
from .orchestrator import DatabaseOrchestrator

__all__ = [
    "DomainRegistry",
    "register_domain",
    "DomainInitializer",
    "DatabaseOrchestrator",
]

