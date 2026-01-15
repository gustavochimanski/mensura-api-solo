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

    def get_by_phone_number_id(self, phone_number_id: str, include_inactive: bool = False) -> Optional[WhatsAppConfigModel]:
        """
        Busca configuração pelo phone_number_id
        
        Args:
            phone_number_id: ID do número de telefone do WhatsApp
            include_inactive: Se True, busca mesmo configurações inativas (prioriza ativas)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not phone_number_id:
            return None
        
        # Normaliza para string e remove espaços
        phone_number_id = str(phone_number_id).strip()
        
        # Primeiro tenta buscar apenas ativas
        query = (
            self.db.query(WhatsAppConfigModel)
            .filter(WhatsAppConfigModel.phone_number_id == phone_number_id)
        )
        
        if not include_inactive:
            query = query.filter(WhatsAppConfigModel.is_active.is_(True))
        
        config = query.order_by(desc(WhatsAppConfigModel.updated_at)).first()
        
        # Se não encontrou e include_inactive=False, tenta buscar inativas também
        if not config and not include_inactive:
            logger.warning(f"Configuração ativa não encontrada para phone_number_id={phone_number_id}, tentando buscar inativas...")
            config = (
                self.db.query(WhatsAppConfigModel)
                .filter(WhatsAppConfigModel.phone_number_id == phone_number_id)
                .order_by(desc(WhatsAppConfigModel.updated_at))
                .first()
            )
            if config:
                logger.warning(f"⚠️ Configuração encontrada mas está INATIVA (is_active={config.is_active}) para phone_number_id={phone_number_id}")
        
        if config:
            logger.info(f"✅ Configuração encontrada: phone_number_id={phone_number_id}, empresa_id={config.empresa_id}, is_active={config.is_active}")
        else:
            logger.warning(f"❌ Nenhuma configuração encontrada para phone_number_id={phone_number_id}")
            # Debug: lista todas as configurações disponíveis
            all_configs = self.db.query(WhatsAppConfigModel).all()
            if all_configs:
                configs_info = [
                    f"(phone_number_id={c.phone_number_id}, empresa_id={c.empresa_id}, is_active={c.is_active})"
                    for c in all_configs
                ]
                logger.warning(f"📋 Configurações disponíveis no banco: {', '.join(configs_info)}")
            else:
                logger.warning("📋 Nenhuma configuração cadastrada no banco de dados")
        
        return config

    def get_by_display_phone_number(self, display_phone_number: str, include_inactive: bool = False) -> Optional[WhatsAppConfigModel]:
        """
        Busca configuração pelo display_phone_number (alternativa para 360dialog)
        
        Args:
            display_phone_number: Número de telefone exibido
            include_inactive: Se True, busca mesmo configurações inativas (prioriza ativas)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not display_phone_number:
            return None
        
        # Normaliza para string e remove espaços
        display_phone_number = str(display_phone_number).strip()
        
        # Primeiro tenta buscar apenas ativas
        query = (
            self.db.query(WhatsAppConfigModel)
            .filter(WhatsAppConfigModel.display_phone_number == display_phone_number)
        )
        
        if not include_inactive:
            query = query.filter(WhatsAppConfigModel.is_active.is_(True))
        
        config = query.order_by(desc(WhatsAppConfigModel.updated_at)).first()
        
        # Se não encontrou e include_inactive=False, tenta buscar inativas também
        if not config and not include_inactive:
            logger.warning(f"Configuração ativa não encontrada para display_phone_number={display_phone_number}, tentando buscar inativas...")
            config = (
                self.db.query(WhatsAppConfigModel)
                .filter(WhatsAppConfigModel.display_phone_number == display_phone_number)
                .order_by(desc(WhatsAppConfigModel.updated_at))
                .first()
            )
            if config:
                logger.warning(f"⚠️ Configuração encontrada mas está INATIVA (is_active={config.is_active}) para display_phone_number={display_phone_number}")
        
        if config:
            logger.info(f"✅ Configuração encontrada: display_phone_number={display_phone_number}, empresa_id={config.empresa_id}, is_active={config.is_active}")
        else:
            logger.warning(f"❌ Nenhuma configuração encontrada para display_phone_number={display_phone_number}")
        
        return config

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

