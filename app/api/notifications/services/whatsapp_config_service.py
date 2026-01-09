from typing import List, Optional, Dict, Any
import logging

from ..repositories.whatsapp_config_repository import WhatsAppConfigRepository
from ..models.whatsapp_config_model import WhatsAppConfigModel

logger = logging.getLogger(__name__)


class WhatsAppConfigService:
    """Regras de negócio para configurações do WhatsApp Business."""

    DEFAULT_BASE_URL = "https://waba-v2.360dialog.io"
    DEFAULT_PROVIDER = "360dialog"

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

        data = self._ensure_defaults(data)
        self._validate_requirements(data)

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

        data = self._ensure_defaults(data, existing=config)
        self._validate_requirements(data, existing=config)

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
            "base_url": config.base_url,
            "provider": config.provider,
            "api_version": config.api_version,
            "send_mode": config.send_mode,
            "coexistence_enabled": config.coexistence_enabled,
            "is_active": config.is_active,
            "webhook_url": config.webhook_url,
            "webhook_verify_token": config.webhook_verify_token,
            "webhook_header_key": config.webhook_header_key,
            "webhook_header_value": config.webhook_header_value,
            "webhook_is_active": config.webhook_is_active,
            "webhook_status": config.webhook_status,
            "webhook_last_sync": config.webhook_last_sync,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }

    def _ensure_defaults(
        self,
        data: Dict[str, Any],
        existing: Optional[WhatsAppConfigModel] = None,
    ) -> Dict[str, Any]:
        """Define valores padrão de base_url/provider para 360dialog quando não enviados."""
        data = dict(data)
        data.setdefault("base_url", existing.base_url if existing else self.DEFAULT_BASE_URL)
        data.setdefault("provider", existing.provider if existing else self.DEFAULT_PROVIDER)
        # Webhook: mantém dados existentes se não enviados
        data.setdefault("webhook_url", existing.webhook_url if existing else None)
        data.setdefault("webhook_verify_token", existing.webhook_verify_token if existing else None)
        data.setdefault("webhook_header_key", existing.webhook_header_key if existing else None)
        data.setdefault("webhook_header_value", existing.webhook_header_value if existing else None)
        data.setdefault("webhook_is_active", existing.webhook_is_active if existing else False)
        data.setdefault("webhook_status", existing.webhook_status if existing else "pending")
        data.setdefault("webhook_last_sync", existing.webhook_last_sync if existing else None)
        return data

    def _validate_requirements(
        self,
        data: Dict[str, Any],
        existing: Optional[WhatsAppConfigModel] = None,
    ) -> None:
        """Valida obrigatoriedades conforme o provedor configurado."""
        provider = (data.get("provider") or (existing.provider if existing else "") or "").lower()
        base_url = (data.get("base_url") or (existing.base_url if existing else "") or "").lower()
        phone_number_id = data.get("phone_number_id") or (existing.phone_number_id if existing else None)
        webhook_url = data.get("webhook_url") or (existing.webhook_url if existing else None)
        webhook_verify_token = data.get("webhook_verify_token") or (
            existing.webhook_verify_token if existing else None
        )
        webhook_header_key = data.get("webhook_header_key") or (
            existing.webhook_header_key if existing else None
        )
        webhook_header_value = data.get("webhook_header_value") or (
            existing.webhook_header_value if existing else None
        )
        # `provider` tem precedência. Se estiver vazio, inferimos pelo base_url (compatibilidade).
        is_360 = (provider == "360dialog") or (not provider and "360dialog" in base_url)

        if not is_360:
            if not phone_number_id:
                raise ValueError("phone_number_id é obrigatório para provedores que não sejam 360dialog")

        if not is_360:
            if not data.get("access_token") and not (existing and existing.access_token):
                raise ValueError("access_token é obrigatório para provedores que não sejam 360dialog")

        if webhook_url and not webhook_verify_token:
            raise ValueError("webhook_verify_token é obrigatório quando webhook_url for enviado")

        if (webhook_header_key and not webhook_header_value) or (webhook_header_value and not webhook_header_key):
            raise ValueError("webhook_header_key e webhook_header_value devem ser enviados juntos")
