from typing import Optional
from datetime import datetime
from pydantic import BaseModel, root_validator


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


class WhatsAppConfigCreate(WhatsAppConfigBase):
    empresa_id: str
    access_token: str
    phone_number_id: Optional[str] = None

    @root_validator
    def ensure_required_fields(cls, values):
        provider = (values.get("provider") or "").lower()
        base_url = (values.get("base_url") or "").lower()
        phone_number_id = values.get("phone_number_id")

        if "360dialog" not in provider and "360dialog" not in base_url:
            if not phone_number_id:
                raise ValueError("phone_number_id é obrigatório para provedores que não sejam 360dialog")

        if not values.get("access_token"):
            raise ValueError("access_token é obrigatório")

        return values


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
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

