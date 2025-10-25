from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

# Schemas de Request
class CreateEventRequest(BaseModel):
    empresa_id: str = Field(..., description="ID da empresa")
    event_type: str = Field(..., description="Tipo do evento")
    event_id: Optional[str] = Field(None, description="ID do recurso que gerou o evento")
    data: Dict[str, Any] = Field(..., description="Dados do evento")
    event_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadados adicionais")

class ProcessEventRequest(BaseModel):
    event_id: str = Field(..., description="ID do evento a ser processado")

# Schemas de Response
class EventResponse(BaseModel):
    id: str
    empresa_id: str
    event_type: str
    event_id: Optional[str]
    data: Dict[str, Any]
    event_metadata: Optional[Dict[str, Any]]
    processed: bool
    processed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class EventListResponse(BaseModel):
    events: List[EventResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

# Schemas de filtro
class EventFilter(BaseModel):
    empresa_id: Optional[str] = None
    event_type: Optional[str] = None
    processed: Optional[bool] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None
