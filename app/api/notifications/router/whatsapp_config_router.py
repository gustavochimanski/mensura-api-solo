from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ....database.db_connection import get_db
from ....core.admin_dependencies import get_current_user
from ..repositories.whatsapp_config_repository import WhatsAppConfigRepository
from ..services.whatsapp_config_service import WhatsAppConfigService
from ..schemas.whatsapp_config_schemas import (
    WhatsAppConfigCreate,
    WhatsAppConfigUpdate,
    WhatsAppConfigResponse,
)

router = APIRouter(prefix="/whatsapp-configs", tags=["WhatsApp Config"])


def get_service(db: Session = Depends(get_db)) -> WhatsAppConfigService:
    repo = WhatsAppConfigRepository(db)
    return WhatsAppConfigService(repo)


@router.get("", response_model=List[WhatsAppConfigResponse])
def list_configs(
    empresa_id: str = Query(..., description="ID da empresa"),
    include_inactive: bool = Query(True, description="Retorna configs inativas também"),
    service: WhatsAppConfigService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    configs = service.list_configs(empresa_id, include_inactive)
    return [WhatsAppConfigService.to_response_dict(cfg) for cfg in configs]


@router.get("/active", response_model=WhatsAppConfigResponse)
def get_active_config(
    empresa_id: str = Query(..., description="ID da empresa"),
    service: WhatsAppConfigService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    config = service.get_active_config(empresa_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma configuração ativa encontrada para a empresa",
        )
    return WhatsAppConfigService.to_response_dict(config)


@router.get("/{config_id}", response_model=WhatsAppConfigResponse)
def get_config(
    config_id: str,
    service: WhatsAppConfigService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    config = service.get_config(config_id)
    if not config:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Configuração não encontrada")
    return WhatsAppConfigService.to_response_dict(config)


@router.post("", response_model=WhatsAppConfigResponse, status_code=status.HTTP_201_CREATED)
def create_config(
    payload: WhatsAppConfigCreate,
    service: WhatsAppConfigService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    config = service.create_config(payload.dict())
    return WhatsAppConfigService.to_response_dict(config)


@router.put("/{config_id}", response_model=WhatsAppConfigResponse)
def update_config(
    config_id: str,
    payload: WhatsAppConfigUpdate,
    service: WhatsAppConfigService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    config = service.update_config(config_id, payload.dict(exclude_unset=True))
    if not config:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Configuração não encontrada")
    return WhatsAppConfigService.to_response_dict(config)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_config(
    config_id: str,
    service: WhatsAppConfigService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    deleted = service.delete_config(config_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Configuração não encontrada")
    return None


@router.post("/{config_id}/activate", response_model=WhatsAppConfigResponse)
def activate_config(
    config_id: str,
    service: WhatsAppConfigService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    config = service.activate_config(config_id)
    if not config:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Configuração não encontrada")
    return WhatsAppConfigService.to_response_dict(config)

