from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class WhatsAppConfigBase(BaseModel):
    name: Optional[str] = None
    display_phone_number: Optional[str] = None
    access_token: str
    phone_number_id: str
    business_account_id: Optional[str] = None
    api_version: Optional[str] = "v22.0"
    send_mode: Optional[str] = "api"
    coexistence_enabled: Optional[bool] = False
    is_active: Optional[bool] = False


class WhatsAppConfigCreate(WhatsAppConfigBase):
    empresa_id: str


class WhatsAppConfigUpdate(BaseModel):
    name: Optional[str] = None
    display_phone_number: Optional[str] = None
    access_token: Optional[str] = None
    phone_number_id: Optional[str] = None
    business_account_id: Optional[str] = None
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
    phone_number_id: str
    business_account_id: Optional[str] = None
    api_version: str
    send_mode: str
    coexistence_enabled: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

