from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.api.chatbot.models.model_chatbot_config import ChatbotConfigModel
from app.utils.logger import logger


class ChatbotConfigRepository:
    """Repository para CRUD de configurações do chatbot"""
    
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, config_id: int) -> Optional[ChatbotConfigModel]:
        """Busca uma configuração por ID com relacionamentos"""
        return (
            self.db.query(ChatbotConfigModel)
            .options(
                joinedload(ChatbotConfigModel.empresa)
            )
            .filter(ChatbotConfigModel.id == config_id)
            .first()
        )

    def get_by_empresa_id(self, empresa_id: int) -> Optional[ChatbotConfigModel]:
        """Busca uma configuração por empresa_id"""
        return (
            self.db.query(ChatbotConfigModel)
            .options(
                joinedload(ChatbotConfigModel.empresa)
            )
            .filter(ChatbotConfigModel.empresa_id == empresa_id)
            .first()
        )

    def list(
        self,
        empresa_id: Optional[int] = None,
        ativo: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ChatbotConfigModel]:
        """Lista configurações com filtros opcionais"""
        query = (
            self.db.query(ChatbotConfigModel)
            .options(
                joinedload(ChatbotConfigModel.empresa)
            )
        )

        if empresa_id:
            query = query.filter(ChatbotConfigModel.empresa_id == empresa_id)
        
        if ativo is not None:
            query = query.filter(ChatbotConfigModel.ativo == ativo)

        query = query.order_by(ChatbotConfigModel.nome.asc())
        query = query.offset(skip)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()

    def create(self, **data) -> ChatbotConfigModel:
        """Cria uma nova configuração"""
        config = ChatbotConfigModel(**data)
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        logger.info(f"[ChatbotConfig] Criado config_id={config.id} empresa_id={config.empresa_id} nome={config.nome}")
        return config

    def update(self, config: ChatbotConfigModel, **data) -> ChatbotConfigModel:
        """Atualiza uma configuração existente"""
        for key, value in data.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)
        self.db.commit()
        self.db.refresh(config)
        return config

    def delete(self, config: ChatbotConfigModel) -> None:
        """Remove uma configuração (soft delete - marca como inativo)"""
        config.ativo = False
        self.db.commit()
        logger.info(f"[ChatbotConfig] Desativado config_id={config.id}")
