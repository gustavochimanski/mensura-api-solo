from sqlalchemy import Column, String, Text, DateTime, JSON, Boolean, Index
from datetime import datetime
import uuid

from ....database.db_connection import Base

class Event(Base):
    __tablename__ = "events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = Column(String, nullable=False, index=True)
    
    # Identificação do evento
    event_type = Column(String, nullable=False, index=True)
    event_id = Column(String, nullable=True, index=True)  # ID do recurso que gerou o evento
    
    # Dados do evento
    data = Column(JSON, nullable=False)
    event_metadata = Column(JSON, nullable=True)
    
    # Controle de processamento
    processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Índices compostos para performance
    __table_args__ = (
        {"schema": "notifications"},
        Index('idx_empresa_event_type', 'empresa_id', 'event_type'),
        Index('idx_empresa_processed', 'empresa_id', 'processed'),
    )
