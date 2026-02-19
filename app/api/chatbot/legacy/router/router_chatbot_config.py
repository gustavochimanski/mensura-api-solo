from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, Path, Body
from sqlalchemy.orm import Session

from app.api.chatbot.services.service_chatbot_config import ChatbotConfigService
from app.api.chatbot.schemas.schema_chatbot_config import (
    ChatbotConfigCreate,
    ChatbotConfigUpdate,
    ChatbotConfigResponse
)
from app.api.cadastros.models.user_model import UserModel
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(
    prefix="/admin/config",
    tags=["Admin - Chatbot (Configurações)"],
    dependencies=[Depends(get_current_user)]
)

# ======================================================================
# ==================== CRUD CONFIGURAÇÕES DO CHATBOT ====================

@router.post("/", response_model=ChatbotConfigResponse, status_code=status.HTTP_201_CREATED)
def criar_configuracao_chatbot(
    data: ChatbotConfigCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Cria uma nova configuração do chatbot para uma empresa.
    
    - **empresa_id**: ID da empresa (obrigatório, única por empresa)
    - **nome**: Nome do chatbot (padrão: "Assistente Virtual")
    - **personalidade**: Descrição da personalidade do chatbot
    - **aceita_pedidos_whatsapp**: Se aceita fazer pedidos pelo WhatsApp (padrão: true). Se false, redireciona para o cardápio online
    - **mensagem_boas_vindas**: Mensagem de boas-vindas personalizada
    - **mensagem_redirecionamento**: Mensagem quando redireciona para link
    - **ativo**: Se a configuração está ativa (padrão: true)
    """
    logger.info(f"[ChatbotConfig] Criar configuração - empresa_id={data.empresa_id} usuario_id={current_user.id}")
    svc = ChatbotConfigService(db)
    return svc.create(data)

@router.get("/", response_model=List[ChatbotConfigResponse], status_code=status.HTTP_200_OK)
def listar_configuracoes_chatbot(
    empresa_id: Optional[int] = Query(None, description="Filtrar por empresa", gt=0),
    ativo: Optional[bool] = Query(None, description="Filtrar por status ativo"),
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(100, ge=1, le=500, description="Limite de registros"),
    db: Session = Depends(get_db),
):
    """
    Lista configurações do chatbot com filtros opcionais.
    """
    svc = ChatbotConfigService(db)
    return svc.list(empresa_id=empresa_id, ativo=ativo, skip=skip, limit=limit)

@router.get("/empresa/{empresa_id}", response_model=Optional[ChatbotConfigResponse], status_code=status.HTTP_200_OK)
def get_configuracao_por_empresa(
    empresa_id: int = Path(..., description="ID da empresa", gt=0),
    db: Session = Depends(get_db),
):
    """
    Busca a configuração do chatbot de uma empresa específica.
    Retorna None se não houver configuração cadastrada.
    """
    svc = ChatbotConfigService(db)
    return svc.get_by_empresa_id(empresa_id)

@router.get("/{config_id}", response_model=ChatbotConfigResponse, status_code=status.HTTP_200_OK)
def get_configuracao_chatbot(
    config_id: int = Path(..., description="ID da configuração", gt=0),
    db: Session = Depends(get_db),
):
    """
    Busca uma configuração específica do chatbot por ID.
    """
    svc = ChatbotConfigService(db)
    return svc.get_by_id(config_id)

@router.put("/{config_id}", response_model=ChatbotConfigResponse, status_code=status.HTTP_200_OK)
def atualizar_configuracao_chatbot(
    config_id: int = Path(..., description="ID da configuração", gt=0),
    data: ChatbotConfigUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Atualiza uma configuração do chatbot.
    
    Todos os campos são opcionais. Apenas os campos fornecidos serão atualizados.
    """
    logger.info(f"[ChatbotConfig] Atualizar config_id={config_id} usuario_id={current_user.id}")
    svc = ChatbotConfigService(db)
    return svc.update(config_id, data)

@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_configuracao_chatbot(
    config_id: int = Path(..., description="ID da configuração", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Remove uma configuração do chatbot (soft delete - marca como inativo).
    """
    logger.info(f"[ChatbotConfig] Deletar config_id={config_id} usuario_id={current_user.id}")
    svc = ChatbotConfigService(db)
    svc.delete(config_id)
    return None
