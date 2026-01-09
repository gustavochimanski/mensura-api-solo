from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.api.cadastros.models.user_model import UserModel
from app.api.cadastros.schemas.schema_meio_pagamento import MeioPagamentoResponse, MeioPagamentoCreate, \
    MeioPagamentoUpdate
from app.api.cadastros.services.service_meio_pagamento import MeioPagamentoService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db

router = APIRouter(prefix="/api/cadastros/admin/meios-pagamento", 
    tags=["Admin - Cadastros - Meios de Pagamento"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/", response_model=List[MeioPagamentoResponse])
def listar_meios_pagamento_admin(db: Session = Depends(get_db)):
    return MeioPagamentoService(db).list_all()

@router.get("/{meio_pagamento_id}", response_model=MeioPagamentoResponse)
def obter_meio_pagamento(meio_pagamento_id: int, db: Session = Depends(get_db)):
    return MeioPagamentoService(db).get(meio_pagamento_id)

@router.post("/", response_model=MeioPagamentoResponse)
def criar_meio_pagamento(data: MeioPagamentoCreate, db: Session = Depends(get_db)):
    return MeioPagamentoService(db).create(data)

@router.put("/{meio_pagamento_id}", response_model=MeioPagamentoResponse)
def atualizar_meio_pagamento(meio_pagamento_id: int, data: MeioPagamentoUpdate, db: Session = Depends(get_db)):
    return MeioPagamentoService(db).update(meio_pagamento_id, data)

@router.delete("/{meio_pagamento_id}")
def deletar_meio_pagamento(meio_pagamento_id: int, db: Session = Depends(get_db)):
    return MeioPagamentoService(db).delete(meio_pagamento_id)
