from sqlalchemy import Column, String, Text, DateTime, JSON, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Event(Base):
    __tablename__ = "events"
    __table_args__ = {"schema": "notifications"}
    
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
        Index('idx_empresa_event_type', 'empresa_id', 'event_type'),
        Index('idx_empresa_processed', 'empresa_id', 'processed'),
    )
