from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.chatbot.repositories.repo_chatbot_config import ChatbotConfigRepository
from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.chatbot.schemas.schema_chatbot_config import (
    ChatbotConfigCreate,
    ChatbotConfigUpdate,
    ChatbotConfigResponse
)
from app.api.chatbot.models.model_chatbot_config import ChatbotConfigModel
from app.utils.logger import logger


class ChatbotConfigService:
    """Service para CRUD de configurações do chatbot"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = ChatbotConfigRepository(db)
        self.repo_empresa = EmpresaRepository(db)

    def _empresa_or_404(self, empresa_id: int):
        """Valida se empresa existe"""
        empresa = self.repo_empresa.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada"
            )
        return empresa

    def _validate_link_redirecionamento(self, aceita_pedidos: bool, link: Optional[str]):
        """Valida se link é obrigatório quando não aceita pedidos"""
        if not aceita_pedidos and not link:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Link de redirecionamento é obrigatório quando não aceita pedidos pelo WhatsApp"
            )

    def create(self, data: ChatbotConfigCreate) -> ChatbotConfigResponse:
        """Cria uma nova configuração do chatbot"""
        self._empresa_or_404(data.empresa_id)
        
        # Verifica se já existe configuração para esta empresa
        existing = self.repo.get_by_empresa_id(data.empresa_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma configuração de chatbot para esta empresa"
            )
        
        # Valida link de redirecionamento
        self._validate_link_redirecionamento(data.aceita_pedidos_whatsapp, data.link_redirecionamento)
        
        config = self.repo.create(
            empresa_id=data.empresa_id,
            nome=data.nome,
            personalidade=data.personalidade,
            aceita_pedidos_whatsapp=data.aceita_pedidos_whatsapp,
            link_redirecionamento=data.link_redirecionamento,
            mensagem_boas_vindas=data.mensagem_boas_vindas,
            mensagem_redirecionamento=data.mensagem_redirecionamento,
            ativo=data.ativo
        )
        
        logger.info(f"[ChatbotConfig] Criado config_id={config.id} empresa_id={data.empresa_id} nome={config.nome}")
        return self._config_to_response(config)

    def get_by_id(self, config_id: int, empresa_id: Optional[int] = None) -> ChatbotConfigResponse:
        """Busca uma configuração por ID, opcionalmente validando empresa"""
        config = self.repo.get_by_id(config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuração do chatbot não encontrada"
            )
        
        # Valida se a configuração pertence à empresa
        if empresa_id and config.empresa_id != empresa_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Configuração não pertence à empresa informada"
            )
        
        return self._config_to_response(config)

    def get_by_empresa_id(self, empresa_id: int) -> Optional[ChatbotConfigResponse]:
        """Busca configuração por empresa_id"""
        config = self.repo.get_by_empresa_id(empresa_id)
        if not config:
            return None
        return self._config_to_response(config)

    def list(
        self,
        empresa_id: Optional[int] = None,
        ativo: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ChatbotConfigResponse]:
        """Lista configurações com filtros"""
        if empresa_id:
            self._empresa_or_404(empresa_id)
        
        configs = self.repo.list(
            empresa_id=empresa_id,
            ativo=ativo,
            skip=skip,
            limit=limit
        )
        
        return [self._config_to_response(c) for c in configs]

    def update(self, config_id: int, data: ChatbotConfigUpdate, empresa_id: Optional[int] = None) -> ChatbotConfigResponse:
        """Atualiza uma configuração"""
        config = self.repo.get_by_id(config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuração do chatbot não encontrada"
            )
        
        # Valida se a configuração pertence à empresa
        if empresa_id and config.empresa_id != empresa_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Configuração não pertence à empresa informada"
            )
        
        # Valida link de redirecionamento se estiver atualizando aceita_pedidos_whatsapp
        update_data = data.model_dump(exclude_unset=True)
        
        # Se está desativando aceita_pedidos_whatsapp, valida link
        if "aceita_pedidos_whatsapp" in update_data:
            aceita_pedidos = update_data.get("aceita_pedidos_whatsapp", config.aceita_pedidos_whatsapp)
            link = update_data.get("link_redirecionamento", config.link_redirecionamento)
            self._validate_link_redirecionamento(aceita_pedidos, link)
        
        config = self.repo.update(config, **update_data)
        
        logger.info(f"[ChatbotConfig] Atualizado config_id={config_id}")
        return self._config_to_response(config)

    def delete(self, config_id: int, empresa_id: Optional[int] = None) -> None:
        """Remove uma configuração (soft delete)"""
        config = self.repo.get_by_id(config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuração do chatbot não encontrada"
            )
        
        # Valida se a configuração pertence à empresa
        if empresa_id and config.empresa_id != empresa_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Configuração não pertence à empresa informada"
            )
        
        self.repo.delete(config)
        logger.info(f"[ChatbotConfig] Removido config_id={config_id}")

    def _config_to_response(self, config: ChatbotConfigModel) -> ChatbotConfigResponse:
        """Converte model para response"""
        return ChatbotConfigResponse(
            id=config.id,
            empresa_id=config.empresa_id,
            nome=config.nome,
            personalidade=config.personalidade,
            aceita_pedidos_whatsapp=config.aceita_pedidos_whatsapp,
            link_redirecionamento=config.link_redirecionamento,
            mensagem_boas_vindas=config.mensagem_boas_vindas,
            mensagem_redirecionamento=config.mensagem_redirecionamento,
            ativo=config.ativo,
            created_at=config.created_at,
            updated_at=config.updated_at,
            empresa_nome=config.empresa.nome if config.empresa else None,
        )
