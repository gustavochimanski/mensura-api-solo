"""
Configurações para integração com Printer API
"""
import os
from typing import Optional


class PrinterConfig:
    """Configurações da Printer API"""
    
    # URL da Printer API
    PRINTER_API_URL: str = os.getenv("PRINTER_API_URL", "http://localhost:8000")
    
    # Timeout para requisições HTTP
    PRINTER_TIMEOUT: int = int(os.getenv("PRINTER_TIMEOUT", "30"))
    
    # Número máximo de pedidos para imprimir por vez
    MAX_PEDIDOS_IMPRESSAO: int = int(os.getenv("MAX_PEDIDOS_IMPRESSAO", "10"))
    
    # Configurações de retry
    PRINTER_RETRY_ATTEMPTS: int = int(os.getenv("PRINTER_RETRY_ATTEMPTS", "3"))
    PRINTER_RETRY_DELAY: int = int(os.getenv("PRINTER_RETRY_DELAY", "2"))  # segundos
    
    @classmethod
    def get_printer_url(cls) -> str:
        """Retorna a URL da Printer API"""
        return cls.PRINTER_API_URL
    
    @classmethod
    def get_timeout(cls) -> int:
        """Retorna o timeout para requisições"""
        return cls.PRINTER_TIMEOUT
    
    @classmethod
    def get_max_pedidos(cls) -> int:
        """Retorna o número máximo de pedidos para imprimir"""
        return cls.MAX_PEDIDOS_IMPRESSAO
