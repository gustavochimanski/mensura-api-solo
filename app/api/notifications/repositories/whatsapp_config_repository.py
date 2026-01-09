from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models.whatsapp_config_model import WhatsAppConfigModel


class WhatsAppConfigRepository:
    """Repositório para configurações do WhatsApp Business."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: Dict[str, Any]) -> WhatsAppConfigModel:
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Creating WhatsAppConfigModel with data: {data}")
        try:
            config = WhatsAppConfigModel(**data)
            logger.info(f"Model created, adding to session")
            self.db.add(config)
            logger.info("Added to session, committing")
            self.db.commit()
            logger.info("Committed, refreshing")
            self.db.refresh(config)
            logger.info(f"Config created successfully: id={config.id}, empresa_id={config.empresa_id}")
            return config
        except Exception as e:
            logger.error(f"Error creating config: {e}")
            self.db.rollback()
            raise

    def list_by_empresa(
        self,
        empresa_id: str,
        include_inactive: bool = True,
    ) -> List[WhatsAppConfigModel]:
        query = (
            self.db.query(WhatsAppConfigModel)
            .filter(WhatsAppConfigModel.empresa_id == str(empresa_id))
        )
        if not include_inactive:
            query = query.filter(WhatsAppConfigModel.is_active.is_(True))
        return query.order_by(desc(WhatsAppConfigModel.created_at)).all()

    def get_by_id(self, config_id: str) -> Optional[WhatsAppConfigModel]:
        return (
            self.db.query(WhatsAppConfigModel)
            .filter(WhatsAppConfigModel.id == config_id)
            .first()
        )

    def get_active_by_empresa(self, empresa_id: str) -> Optional[WhatsAppConfigModel]:
        return (
            self.db.query(WhatsAppConfigModel)
            .filter(
                WhatsAppConfigModel.empresa_id == str(empresa_id),
                WhatsAppConfigModel.is_active.is_(True),
            )
            .order_by(desc(WhatsAppConfigModel.updated_at))
            .first()
        )

    def get_last_active(self) -> Optional[WhatsAppConfigModel]:
        return (
            self.db.query(WhatsAppConfigModel)
            .filter(WhatsAppConfigModel.is_active.is_(True))
            .order_by(desc(WhatsAppConfigModel.updated_at))
            .first()
        )

    def get_by_phone_number_id(self, phone_number_id: str) -> Optional[WhatsAppConfigModel]:
        """Busca configuração pelo phone_number_id"""
        return (
            self.db.query(WhatsAppConfigModel)
            .filter(WhatsAppConfigModel.phone_number_id == phone_number_id)
            .filter(WhatsAppConfigModel.is_active.is_(True))
            .order_by(desc(WhatsAppConfigModel.updated_at))
            .first()
        )

    def deactivate_all(self, empresa_id: str) -> None:
        import logging
        logger = logging.getLogger(__name__)

        result = (
            self.db.query(WhatsAppConfigModel)
            .filter(WhatsAppConfigModel.empresa_id == str(empresa_id))
            .update({"is_active": False})
        )
        logger.info(f"Deactivated {result} configs for empresa_id: {empresa_id}")
        # Note: We don't commit here, let the caller handle the transaction

    def update(self, config_id: str, data: Dict[str, Any]) -> Optional[WhatsAppConfigModel]:
        config = self.get_by_id(config_id)
        if not config:
            return None

        for key, value in data.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)

        self.db.commit()
        self.db.refresh(config)
        return config

    def delete(self, config_id: str) -> bool:
        config = self.get_by_id(config_id)
        if not config:
            return False

        self.db.delete(config)
        self.db.commit()
        return True

