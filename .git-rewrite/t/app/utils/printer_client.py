"""
Cliente para comunicação com a Printer API
"""
import httpx
from typing import Dict, Any, Optional
from app.utils.logger import logger


class PrinterClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.timeout = 30.0
    
    async def imprimir_pedido(self, pedido_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envia pedido para impressão via Printer API
        
        Args:
            pedido_data: Dados do pedido no formato esperado pela Printer API
            
        Returns:
            Dict com resultado da impressão
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/print",
                    json=pedido_data
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.TimeoutException:
            logger.error(f"[PrinterClient] Timeout ao imprimir pedido #{pedido_data.get('numero')}")
            return {
                "sucesso": False,
                "mensagem": "Timeout na comunicação com a impressora"
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"[PrinterClient] Erro HTTP {e.response.status_code} ao imprimir pedido #{pedido_data.get('numero')}: {e.response.text}")
            return {
                "sucesso": False,
                "mensagem": f"Erro HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            logger.error(f"[PrinterClient] Erro inesperado ao imprimir pedido #{pedido_data.get('numero')}: {str(e)}")
            return {
                "sucesso": False,
                "mensagem": f"Erro inesperado: {str(e)}"
            }
    
    async def verificar_saude(self) -> bool:
        """
        Verifica se a Printer API está funcionando
        
        Returns:
            True se a API está funcionando, False caso contrário
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"[PrinterClient] Erro ao verificar saúde da Printer API: {str(e)}")
            return False
