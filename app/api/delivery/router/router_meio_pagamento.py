from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.api.delivery.schemas.schema_meio_pagamento import MeioPagamentoResponse, MeioPagamentoCreate, \
    MeioPagamentoUpdate
from app.api.delivery.services.meio_pagamento_service import MeioPagamentoService
from app.core.admin_dependencies import get_current_user
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from fastapi import Depends, HTTPException

router = APIRouter(prefix="/api/delivery/meios-pagamento", tags=["Meios de Pagamento"])



def dependency_a():
    return get_current_user()


def dependency_b():
    return get_cliente_by_super_token()


@router.get("/")
def listar_meios_pagamento(
        db: Session = Depends(get_db),
        token_a: str | None = Depends(lambda: dependency_a()),
        token_b: str | None = Depends(lambda: dependency_b()),
):
    # só precisa que um dos dois passe
    if not (token_a or token_b):
        raise HTTPException(status_code=401, detail="Não autorizado")

    return MeioPagamentoService(db).list_all()


@router.get("/{meio_pagamento_id}", response_model=MeioPagamentoResponse, dependencies=[Depends(get_current_user)])
def obter_meio_pagamento(meio_pagamento_id: int, db: Session = Depends(get_db)):
    return MeioPagamentoService(db).get(meio_pagamento_id)

@router.post("/", response_model=MeioPagamentoResponse, dependencies=[Depends(get_current_user)])
def criar_meio_pagamento(data: MeioPagamentoCreate, db: Session = Depends(get_db)):
    return MeioPagamentoService(db).create(data)

@router.put("/{meio_pagamento_id}", response_model=MeioPagamentoResponse, dependencies=[Depends(get_current_user)])
def atualizar_meio_pagamento(meio_pagamento_id: int, data: MeioPagamentoUpdate, db: Session = Depends(get_db)):
    return MeioPagamentoService(db).update(meio_pagamento_id, data)

@router.delete("/{meio_pagamento_id}", dependencies=[Depends(get_current_user)])
def deletar_meio_pagamento(meio_pagamento_id: int, db: Session = Depends(get_db)):
    return MeioPagamentoService(db).delete(meio_pagamento_id)
