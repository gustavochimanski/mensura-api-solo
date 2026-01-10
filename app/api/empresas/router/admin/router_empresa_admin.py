# app/api/empresas/router/admin/router_empresa_admin.py
from fastapi import APIRouter, Depends, UploadFile, Form, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
import json
from functools import lru_cache

from app.database.db_connection import get_db
from app.core.admin_dependencies import get_current_user
from app.api.empresas.schemas.schema_empresa import (
    EmpresaCreate,
    EmpresaUpdate,
    EmpresaResponse,
    EmpresaCardapioLinkResponse,
)
from app.api.empresas.services.empresa_service import EmpresaService
from app.utils.slug_utils import make_slug
from app.api.localizacao.adapters.google_maps_adapter import GoogleMapsAdapter
from app.utils.logger import logger

router = APIRouter(
    tags=["Admin - Empresas"],
    dependencies=[Depends(get_current_user)]
)


@lru_cache(maxsize=1)
def get_google_maps_adapter() -> GoogleMapsAdapter:
    """Dependency para obter adapter do Google Maps (singleton)."""
    return GoogleMapsAdapter()


@router.get("/buscar-endereco", status_code=status.HTTP_200_OK)
def buscar_endereco(
    text: str = Query(..., description="Texto para buscar endereços"),
    max_results: int = Query(5, ge=1, le=10, description="Número máximo de resultados"),
    google_adapter: GoogleMapsAdapter = Depends(get_google_maps_adapter),
):
    """
    Busca endereços baseado em um texto de busca.
    
    Retorna uma lista de endereços encontrados com suas coordenadas.
    """
    logger.info(f"[Empresas] Buscando endereços para: {text}")
    
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


@router.get("/cardapios", response_model=List[EmpresaCardapioLinkResponse])
def list_cardapio_links(db: Session = Depends(get_db)):
    return EmpresaService(db).list_cardapio_links()


# Criar empresa
@router.post("/", response_model=EmpresaResponse)
async def create_empresa(
    nome: str = Form(...),
    cnpj: str | None = Form(None),
    endereco: str = Form(...),  # JSON string com campos de endereço
    horarios_funcionamento: str | None = Form(None),  # JSON string com horários
    timezone: str | None = Form("America/Sao_Paulo"),
    logo: UploadFile | None = None,
    cardapio_link: str | None = Form(None),
    cardapio_tema: str | None = Form("padrao"),
    aceita_pedido_automatico: str | None = Form("false"),
    tempo_entrega_maximo: int = Form(...),
    db: Session = Depends(get_db),
):
    try:
        endereco_data = json.loads(endereco)
    except Exception:
        raise HTTPException(status_code=400, detail="Campo 'endereco' deve ser um JSON válido (string).")

    if horarios_funcionamento:
        try:
            horarios_data = json.loads(horarios_funcionamento)
        except Exception:
            raise HTTPException(status_code=400, detail="Campo 'horarios_funcionamento' deve ser um JSON válido (string).")
    else:
        horarios_data = None
    slug = make_slug(nome)
    empresa_data = EmpresaCreate(
        nome=nome,
        cnpj=cnpj,
        slug=slug,
        timezone=timezone,
        horarios_funcionamento=horarios_data,
        cardapio_link=cardapio_link,
        cardapio_tema=cardapio_tema,
        aceita_pedido_automatico = aceita_pedido_automatico.lower() == "true",
        tempo_entrega_maximo=tempo_entrega_maximo,
        **endereco_data,
    )
    return EmpresaService(db).create_empresa(empresa_data, logo=logo)

# Atualizar empresa
@router.put("/{id}", response_model=EmpresaResponse)
async def update_empresa(
    id: int,
    nome: str | None = Form(None),
    cnpj: str | None = Form(None),
    endereco: str | None = Form(None),  # JSON string com campos de endereço
    horarios_funcionamento: str | None = Form(None),  # JSON string com horários
    timezone: str | None = Form(None),
    logo: UploadFile | None = None,
    cardapio_link: str | None = Form(None),
    cardapio_tema: str | None = Form(None),
    aceita_pedido_automatico: str | None = Form(None),
    tempo_entrega_maximo: int | None = Form(None),
    db: Session = Depends(get_db),
):
    slug = make_slug(nome) if nome else None
    if endereco:
        try:
            endereco_payload = json.loads(endereco)
        except Exception:
            raise HTTPException(status_code=400, detail="Campo 'endereco' deve ser um JSON válido (string).")
    else:
        endereco_payload = {}

    if horarios_funcionamento:
        try:
            horarios_payload = json.loads(horarios_funcionamento)
        except Exception:
            raise HTTPException(status_code=400, detail="Campo 'horarios_funcionamento' deve ser um JSON válido (string).")
    else:
        horarios_payload = None
    empresa_data = EmpresaUpdate(
        nome=nome,
        cnpj=cnpj,
        slug=slug,
        timezone=timezone,
        horarios_funcionamento=horarios_payload,
        cardapio_link=cardapio_link,
        cardapio_tema=cardapio_tema,
        aceita_pedido_automatico = aceita_pedido_automatico.lower() == "true" if aceita_pedido_automatico else None,
        tempo_entrega_maximo=tempo_entrega_maximo,
        **endereco_payload,
    )
    return EmpresaService(db).update_empresa(id=id, data=empresa_data, logo=logo)



# Pegar uma empresa pelo id
@router.get("/{id}", response_model=EmpresaResponse)
def get_empresa(id: int, db: Session = Depends(get_db)):
    return EmpresaService(db).get_empresa(id)


# Listar empresas
@router.get("/", response_model=List[EmpresaResponse])
def list_empresas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return EmpresaService(db).list_empresas(skip, limit)


# Deletar empresa
@router.delete("/{id}", status_code=204)
def delete_empresa(id: int, db: Session = Depends(get_db)):
    EmpresaService(db).delete_empresa(id)

