"""
Registry de inicializadores de domínio.
Permite registro automático e descoberta de domínios.
"""
from typing import List, Dict, Type, Optional
import logging

from .base import DomainInitializer

logger = logging.getLogger(__name__)


class DomainRegistry:
    """
    Registry central para inicializadores de domínio.
    
    Usa o padrão Singleton para garantir uma única instância global.
    """
    _instance: Optional['DomainRegistry'] = None
    _initializers: Dict[str, DomainInitializer] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, initializer: DomainInitializer) -> None:
        """
        Registra um inicializador de domínio.
        
        Args:
            initializer: Instância do inicializador de domínio
            
        Raises:
            ValueError: Se o domínio já estiver registrado
        """
        domain_name = initializer.get_domain_name()
        
        if domain_name in self._initializers:
            logger.warning(f"⚠️ Domínio '{domain_name}' já está registrado. Substituindo...")
        
        self._initializers[domain_name] = initializer
        logger.debug(f"📝 Domínio '{domain_name}' registrado no registry")
    
    def get(self, domain_name: str) -> Optional[DomainInitializer]:
        """
        Retorna o inicializador de um domínio específico.
        
        Args:
            domain_name: Nome do domínio
            
        Returns:
            Inicializador do domínio ou None se não encontrado
        """
        return self._initializers.get(domain_name)
    
    def get_all(self) -> List[DomainInitializer]:
        """
        Retorna todos os inicializadores registrados.
        
        Returns:
            Lista de inicializadores na ordem de registro
        """
        return list(self._initializers.values())
    
    def clear(self) -> None:
        """Limpa o registry (útil para testes)."""
        self._initializers.clear()
        logger.debug("🗑️ Registry limpo")
    
    def count(self) -> int:
        """Retorna o número de domínios registrados."""
        return len(self._initializers)


# Instância global do registry
_registry = DomainRegistry()


def register_domain(initializer: DomainInitializer) -> None:
    """
    Função helper para registrar um domínio.
    
    Args:
        initializer: Instância do inicializador de domínio
    """
    _registry.register(initializer)


def get_registry() -> DomainRegistry:
    """
    Retorna a instância global do registry.
    
    Returns:
        Instância do DomainRegistry
    """
    return _registry

