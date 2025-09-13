from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import re
from app.utils.logger import logger


class ViaCepResponse(BaseModel):
    cep: str
    logradouro: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    localidade: Optional[str] = None
    uf: Optional[str] = None
    ibge: Optional[str] = None
    gia: Optional[str] = None
    ddd: Optional[str] = None
    siafi: Optional[str] = None
    erro: Optional[bool] = None


class ViaCepClient:
    BASE_URL = "https://viacep.com.br/ws"

    def __init__(self):
        pass

    def _validar_cep(self, cep: str) -> bool:
        """Valida se o CEP está no formato correto (8 dígitos)"""
        # Remove caracteres não numéricos
        cep_limpo = re.sub(r'\D', '', cep)
        # Verifica se tem exatamente 8 dígitos
        return len(cep_limpo) == 8 and cep_limpo.isdigit()

    def _limpar_cep(self, cep: str) -> str:
        """Remove caracteres não numéricos do CEP"""
        return re.sub(r'\D', '', cep)

    async def buscar_cep(self, cep: str) -> Optional[ViaCepResponse]:
        """
        Busca informações do endereço pelo CEP usando a API do ViaCEP
        """
        # Valida o formato do CEP
        if not self._validar_cep(cep):
            return None
        
        # Limpa o CEP
        cep_limpo = self._limpar_cep(cep)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.BASE_URL}/{cep_limpo}/json/")
                
            if response.status_code == 200:
                data = response.json()
                
                # Verifica se retornou erro
                if data.get("erro"):
                    return None
                
                # Cria o objeto de resposta
                viacep_response = ViaCepResponse(**data)
                return viacep_response
            else:
                logger.error(f"[ViaCEP] Erro na API: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"[ViaCEP] Erro ao consultar CEP {cep_limpo}: {e}")
            return None

    def extrair_cep_da_query(self, query: str) -> Optional[str]:
        """
        Extrai um CEP de uma string de consulta
        Procura por padrões de CEP (8 dígitos com ou sem hífen)
        """
        # Padrão para CEP: 8 dígitos, opcionalmente com hífen no meio
        cep_pattern = r'\b\d{5}-?\d{3}\b'
        matches = re.findall(cep_pattern, query)
        
        if matches:
            return matches[0]
        
        return None
