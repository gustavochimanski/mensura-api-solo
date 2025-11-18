from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from typing import Optional
from pydantic import BaseModel
from functools import lru_cache

from app.core.admin_dependencies import get_current_user
from app.api.localizacao.adapters.google_maps_adapter import GoogleMapsAdapter
from app.utils.logger import logger


router = APIRouter(
    prefix="/api/localizacao",
    tags=["Localização"]
)


class EnderecoGeocodificar(BaseModel):
    endereco: str


class CoordenadasInput(BaseModel):
    latitude: float
    longitude: float


class CalcularDistanciaRequest(BaseModel):
    origem: CoordenadasInput
    destino: CoordenadasInput
    mode: Optional[str] = "driving"


@lru_cache(maxsize=1)
def get_google_maps_adapter() -> GoogleMapsAdapter:
    """Dependency para obter adapter do Google Maps (singleton)."""
    return GoogleMapsAdapter()


@router.get("/buscar-endereco", status_code=status.HTTP_200_OK)
def buscar_endereco(
    text: str = Query(..., description="Texto para buscar endereços"),
    max_results: int = Query(5, ge=1, le=10, description="Número máximo de resultados"),
    google_adapter: GoogleMapsAdapter = Depends(get_google_maps_adapter),
    _current_user = Depends(get_current_user),
):
    """
    Busca endereços baseado em um texto de busca.
    
    Retorna uma lista de endereços encontrados com suas coordenadas.
    
    Requer autenticação de admin.
    """
    logger.info(f"[Localizacao] Buscando endereços para: {text}")
    
    # Verifica se a API key está configurada
    if not google_adapter.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de geolocalização não configurado. Verifique a configuração da API key do Google Maps."
        )
    
    resultados = google_adapter.buscar_enderecos(text, max_results=max_results)
    
    if not resultados:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum endereço encontrado para: {text}. Verifique os logs para mais detalhes sobre possíveis problemas com a API key."
        )
    
    # Retorna lista direta de resultados como o front-end espera
    return resultados


@router.post("/geocodificar", status_code=status.HTTP_200_OK)
def geocodificar_endereco(
    payload: EnderecoGeocodificar = Body(...),
    google_adapter: GoogleMapsAdapter = Depends(get_google_maps_adapter),
    _current_user = Depends(get_current_user),
):
    """
    Geocodifica um endereço retornando coordenadas latitude/longitude.
    
    Requer autenticação de admin.
    """
    logger.info(f"[Localizacao] Geocodificando endereço: {payload.endereco}")
    
    if not google_adapter.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de geolocalização não configurado. Verifique a configuração da API key do Google Maps."
        )
    
    coords = google_adapter.resolver_coordenadas(payload.endereco)
    if coords is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Não foi possível geocodificar o endereço: {payload.endereco}"
        )
    
    latitude, longitude = coords
    return {
        "endereco": payload.endereco,
        "latitude": latitude,
        "longitude": longitude
    }


@router.post("/calcular-distancia", status_code=status.HTTP_200_OK)
def calcular_distancia(
    payload: CalcularDistanciaRequest = Body(...),
    google_adapter: GoogleMapsAdapter = Depends(get_google_maps_adapter),
    _current_user = Depends(get_current_user),
):
    """
    Calcula distância em km entre duas coordenadas.
    
    Requer autenticação de admin.
    """
    origem = (payload.origem.latitude, payload.origem.longitude)
    destino = (payload.destino.latitude, payload.destino.longitude)
    
    logger.info(f"[Localizacao] Calculando distância entre {origem} e {destino}")
    
    if not google_adapter.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de geolocalização não configurado. Verifique a configuração da API key do Google Maps."
        )
    
    distancia_km = google_adapter.calcular_distancia_km(origem, destino, mode=payload.mode)
    if distancia_km is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível calcular a distância entre os pontos fornecidos"
        )
    
    return {
        "origem": {"latitude": payload.origem.latitude, "longitude": payload.origem.longitude},
        "destino": {"latitude": payload.destino.latitude, "longitude": payload.destino.longitude},
        "distancia_km": round(distancia_km, 3),
        "mode": payload.mode
    }



