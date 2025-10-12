from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.api.delivery.schemas.schema_meio_pagamento import MeioPagamentoResponse, MeioPagamentoCreate, \
    MeioPagamentoUpdate
from app.api.delivery.services.meio_pagamento_service import MeioPagamentoService
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db

router = APIRouter(prefix="/api/delivery/client/meios-pagamento", 
    tags=["Client - Delivery - Meios de Pagamento "],
    dependencies=[Depends(get_cliente_by_super_token)]
)

@router.get("/", response_model=List[MeioPagamentoResponse])
def listar_meios_pagamento(db: Session = Depends(get_db)):
    return MeioPagamentoService(db).list_all()

