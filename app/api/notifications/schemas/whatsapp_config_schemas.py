from typing import Optional
from datetime import datetime
from pydantic import BaseModel, model_validator


class WhatsAppConfigBase(BaseModel):
    name: Optional[str] = None
    display_phone_number: Optional[str] = None
    business_account_id: Optional[str] = None
    base_url: Optional[str] = "https://waba-v2.360dialog.io"
    provider: Optional[str] = "360dialog"
    api_version: Optional[str] = "v22.0"
    send_mode: Optional[str] = "api"
    coexistence_enabled: Optional[bool] = False
    is_active: Optional[bool] = False
    webhook_url: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    webhook_is_active: Optional[bool] = False
    webhook_status: Optional[str] = "pending"
    webhook_last_sync: Optional[datetime] = None


class WhatsAppConfigCreate(WhatsAppConfigBase):
    empresa_id: str
    access_token: Optional[str] = None
    phone_number_id: Optional[str] = None

    @model_validator(mode='after')
    def ensure_required_fields(self):
        provider = (self.provider or "").lower()
        base_url = (self.base_url or "").lower()
        phone_number_id = self.phone_number_id
        webhook_url = self.webhook_url
        webhook_verify_token = self.webhook_verify_token

        is_360 = "360dialog" in provider or "360dialog" in base_url

        if not is_360:
            if not phone_number_id:
                raise ValueError("phone_number_id é obrigatório para provedores que não sejam 360dialog")

        if not is_360 and not self.access_token:
            raise ValueError("access_token é obrigatório para provedores que não sejam 360dialog")

        if webhook_url and not webhook_verify_token:
            raise ValueError("webhook_verify_token é obrigatório quando webhook_url for enviado")

        return self


class WhatsAppConfigUpdate(BaseModel):
    empresa_id: Optional[str] = None
    name: Optional[str] = None
    display_phone_number: Optional[str] = None
    access_token: Optional[str] = None
    phone_number_id: Optional[str] = None
    business_account_id: Optional[str] = None
    base_url: Optional[str] = None
    provider: Optional[str] = None
    api_version: Optional[str] = None
    send_mode: Optional[str] = None
    coexistence_enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    webhook_url: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    webhook_is_active: Optional[bool] = None
    webhook_status: Optional[str] = None
    webhook_last_sync: Optional[datetime] = None


class WhatsAppConfigResponse(BaseModel):
    id: str
    empresa_id: str
    name: Optional[str] = None
    display_phone_number: Optional[str] = None
    access_token: str
    phone_number_id: Optional[str] = None
    business_account_id: Optional[str] = None
    base_url: Optional[str] = None
    provider: Optional[str] = None
    api_version: str
    send_mode: str
    coexistence_enabled: bool
    is_active: bool
    webhook_url: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    webhook_is_active: bool
    webhook_status: Optional[str] = None
    webhook_last_sync: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

