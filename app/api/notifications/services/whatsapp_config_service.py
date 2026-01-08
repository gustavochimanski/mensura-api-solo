from typing import List, Optional, Dict, Any
import logging

from ..repositories.whatsapp_config_repository import WhatsAppConfigRepository
from ..models.whatsapp_config_model import WhatsAppConfigModel

logger = logging.getLogger(__name__)


class WhatsAppConfigService:
    """Regras de negócio para configurações do WhatsApp Business."""

    def __init__(self, repo: WhatsAppConfigRepository):
        self.repo = repo

    def list_configs(self, empresa_id: str, include_inactive: bool = True) -> List[WhatsAppConfigModel]:
        return self.repo.list_by_empresa(empresa_id, include_inactive)

    def get_config(self, config_id: str) -> Optional[WhatsAppConfigModel]:
        return self.repo.get_by_id(config_id)

    def get_active_config(self, empresa_id: Optional[str]) -> Optional[WhatsAppConfigModel]:
        if empresa_id:
            # Retorna apenas a configuração da empresa informada
            return self.repo.get_active_by_empresa(empresa_id)
        # Fallback: última configuração ativa independente da empresa (mantém compatibilidade)
        # Só usado quando empresa_id é None
        return self.repo.get_last_active()

    def create_config(self, data: Dict[str, Any]) -> WhatsAppConfigModel:
        empresa_id = str(data["empresa_id"])

        # Se marcada como ativa, desativa demais
        if data.get("is_active"):
            self.repo.deactivate_all(empresa_id)
        else:
            # Se não há ativo para a empresa, força ativar o primeiro cadastrado
            if not self.repo.get_active_by_empresa(empresa_id):
                data["is_active"] = True

        return self.repo.create(data)

    def update_config(self, config_id: str, data: Dict[str, Any]) -> Optional[WhatsAppConfigModel]:
        config = self.repo.get_by_id(config_id)
        if not config:
            return None

        should_activate = data.get("is_active") is True

        updated = self.repo.update(config_id, data)

        if should_activate and updated:
            self.repo.deactivate_all(updated.empresa_id)
            updated = self.repo.update(config_id, {"is_active": True})

        return updated

    def activate_config(self, config_id: str) -> Optional[WhatsAppConfigModel]:
        config = self.repo.get_by_id(config_id)
        if not config:
            return None

        self.repo.deactivate_all(config.empresa_id)
        return self.repo.update(config_id, {"is_active": True})

    def delete_config(self, config_id: str) -> bool:
        config = self.repo.get_by_id(config_id)
        if not config:
            return False

        empresa_id = config.empresa_id
        was_active = config.is_active

        deleted = self.repo.delete(config_id)

        if deleted and was_active:
            # Se apagar ativo, promove o mais recente para ativo
            remaining = self.repo.list_by_empresa(empresa_id, include_inactive=True)
            if remaining:
                newest = remaining[0]
                self.repo.deactivate_all(empresa_id)
                self.repo.update(newest.id, {"is_active": True})

        return deleted

    @staticmethod
    def to_response_dict(config: WhatsAppConfigModel) -> Dict[str, Any]:
        return {
            "id": config.id,
            "empresa_id": config.empresa_id,
            "name": config.name,
            "display_phone_number": config.display_phone_number,
            "phone_number_id": config.phone_number_id,
            "business_account_id": config.business_account_id,
            "access_token": config.access_token,
            "api_version": config.api_version,
            "send_mode": config.send_mode,
            "coexistence_enabled": config.coexistence_enabled,
            "is_active": config.is_active,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }

