from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from typing import Optional
from pydantic import BaseModel
from functools import lru_cache

from app.core.admin_dependencies import get_current_user
from app.api.localizacao.contracts.geolocalizacao_contract import IGeolocalizacaoService
from app.api.localizacao.models.coordenadas import Coordenadas
from app.api.localizacao.adapters.google_maps_adapter import GoogleMapsAdapter
from app.api.localizacao.adapters.cache_adapter import CacheAdapter
from app.api.localizacao.services.geolocalizacao_service import GeolocalizacaoService
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
def _get_geolocalizacao_service_instance() -> IGeolocalizacaoService:
    """Cria uma instância singleton do serviço de geolocalização."""
    google_adapter = GoogleMapsAdapter()
    cache = CacheAdapter()
    return GeolocalizacaoService(
        geocodificacao_provider=google_adapter,
        distancia_provider=google_adapter,
        cache=cache
    )


def get_geolocalizacao_service() -> IGeolocalizacaoService:
    """Dependency para obter serviço de geolocalização (singleton)."""
    return _get_geolocalizacao_service_instance()


@lru_cache(maxsize=1)
def _get_google_maps_adapter_instance() -> GoogleMapsAdapter:
    """Cria uma instância singleton do adapter do Google Maps."""
    return GoogleMapsAdapter()


def get_google_maps_adapter() -> GoogleMapsAdapter:
    """Dependency para obter adapter do Google Maps (singleton)."""
    return _get_google_maps_adapter_instance()


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
    
    resultados = google_adapter.buscar_enderecos(text, max_results=max_results)
    
    if not resultados:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum endereço encontrado para: {text}"
        )
    
    return {
        "query": text,
        "total": len(resultados),
        "resultados": resultados
    }


@router.post("/geocodificar", status_code=status.HTTP_200_OK)
def geocodificar_endereco(
    payload: EnderecoGeocodificar = Body(...),
    geo_service: IGeolocalizacaoService = Depends(get_geolocalizacao_service),
    _current_user = Depends(get_current_user),
):
    """
    Geocodifica um endereço retornando coordenadas latitude/longitude.
    
    Requer autenticação de admin.
    """
    logger.info(f"[Localizacao] Geocodificando endereço: {payload.endereco}")
    
    coords = geo_service.obter_coordenadas(payload.endereco)
    if coords is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Não foi possível geocodificar o endereço: {payload.endereco}"
        )
    
    return {
        "endereco": payload.endereco,
        "latitude": coords.latitude,
        "longitude": coords.longitude
    }


@router.post("/calcular-distancia", status_code=status.HTTP_200_OK)
def calcular_distancia(
    payload: CalcularDistanciaRequest = Body(...),
    geo_service: IGeolocalizacaoService = Depends(get_geolocalizacao_service),
    _current_user = Depends(get_current_user),
):
    """
    Calcula distância em km entre duas coordenadas.
    
    Requer autenticação de admin.
    """
    origem = Coordenadas(latitude=payload.origem.latitude, longitude=payload.origem.longitude)
    destino = Coordenadas(latitude=payload.destino.latitude, longitude=payload.destino.longitude)
    
    logger.info(f"[Localizacao] Calculando distância entre {origem.to_tuple()} e {destino.to_tuple()}")
    
    distancia_km = geo_service.calcular_distancia(origem, destino, mode=payload.mode)
    if distancia_km is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Não foi possível calcular a distância entre os pontos fornecidos"
        )
    
    return {
        "origem": {"latitude": origem.latitude, "longitude": origem.longitude},
        "destino": {"latitude": destino.latitude, "longitude": destino.longitude},
        "distancia_km": round(distancia_km, 3),
        "mode": payload.mode
    }


@router.delete("/cache", status_code=status.HTTP_200_OK)
def limpar_cache(
    cache_key: Optional[str] = Query(None, description="Chave específica para limpar, ou None para limpar tudo"),
    geo_service: IGeolocalizacaoService = Depends(get_geolocalizacao_service),
    _current_user = Depends(get_current_user),
):
    """
    Limpa o cache de coordenadas geocodificadas.
    
    Requer autenticação de admin.
    """
    geo_service.limpar_cache(cache_key=cache_key)
    return {
        "message": f"Cache limpo: {'chave específica' if cache_key else 'tudo'}",
        "cache_key": cache_key
    }

