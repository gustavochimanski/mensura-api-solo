from sqlalchemy import Column, String, Boolean, DateTime, Text
from datetime import datetime
import uuid

from app.database.db_connection import Base


class WhatsAppConfigModel(Base):
    """Configuração de credenciais do WhatsApp Business por empresa/telefone."""

    __tablename__ = "whatsapp_configs"
    __table_args__ = {"schema": "notifications"}

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)
    display_phone_number = Column(String, nullable=True)
    phone_number_id = Column(String, nullable=True, index=True)
    business_account_id = Column(String, nullable=True)
    access_token = Column(Text, nullable=False)
    base_url = Column(String, nullable=True, default="https://waba-v2.360dialog.io")
    provider = Column(String, nullable=True, default="360dialog")
    api_version = Column(String, nullable=False, default="v22.0")
    send_mode = Column(String, nullable=False, default="api")
    coexistence_enabled = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    # Campos específicos 360dialog / Webhook
    webhook_url = Column(String, nullable=True)
    webhook_verify_token = Column(String, nullable=True)
    webhook_is_active = Column(Boolean, nullable=False, default=False)
    webhook_status = Column(String, nullable=True, default="pending")
    webhook_last_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

