from typing import List

from fastapi import APIRouter, Depends, status, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.cadastros.models.model_cliente_dv import ClienteModel, default_super_token
from app.api.cadastros.repositories.repo_cliente import ClienteRepository
from app.api.cadastros.schemas.schema_cliente import ClienteOut, ClienteUpdate, ClienteCreate
from app.api.cadastros.schemas.schema_endereco import EnderecoOut
from app.api.cadastros.services.service_cliente import ClienteService
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/cadastros/client/clientes", tags=["Client - Cadastros - Clientes"])

class NovoDispositivoRequest(BaseModel):
    telefone: str

# ======================================================================
# ============================ CLIENTE =================================
# ======================================================================
@router.post("/novo-dispositivo", status_code=status.HTTP_200_OK)
def novo_dispositivo(body: NovoDispositivoRequest, db: Session = Depends(get_db)):
    """
    Endpoint para novo dispositivo (login cliente).
    Gera um novo super_token, grava no banco e retorna para o cliente.
    Aceita telefone com um 9 a mais ou a menos: se logar com 9 a menos (ex: 1189999999)
    e no banco estiver com o 9 (11999999999), o cliente é encontrado e o login é retornado.
    """
    repo = ClienteRepository(db)
    cliente = repo.get_by_telefone(body.telefone)
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Telefone não cadastrado")

    # Gera um novo token
    novo_token = default_super_token()
    
    # Atualiza o token do cliente
    cliente.super_token = novo_token
    db.commit()
    db.refresh(cliente)

    logger.info(f"[Novo Dispositivo] Novo token gerado para telefone: {telefone}")
    
    return {
        "super_token": novo_token,
        "nome": cliente.nome,
        "telefone": cliente.telefone
    }

@router.post("/", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def create_new_cliente(data: ClienteCreate, db: Session = Depends(get_db)):
    logger.info("[Cliente] Create")
    service = ClienteService(db)
    cliente = service.create(data)

    # ✅ Garante que todos os campos do schema ClienteOut estejam presentes
    return ClienteOut.model_validate(cliente)

@router.get("/me", response_model=ClienteOut, status_code=status.HTTP_200_OK)
def read_current_cliente(cliente: ClienteModel = Depends(get_cliente_by_super_token)):
    logger.info(f"[Cliente] Get current {cliente.telefone}")

    if not cliente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")

    return ClienteOut.model_validate(cliente)



@router.put("/me", response_model=ClienteOut, status_code=status.HTTP_200_OK)
def update_current_cliente(
    data: ClienteUpdate,
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
    db: Session = Depends(get_db)
):
    logger.info(f"[Cliente] Update {cliente.telefone}")

    if not cliente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")

    service = ClienteService(db)
    updated_cliente = service.update(cliente.super_token, data)

    return ClienteOut.model_validate(updated_cliente)




