from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.api.delivery.schemas.schema_cliente import ClienteOut, ClienteUpdate, ClienteCreate, NovoDispositivoRequest, \
    ConfirmacaoCodigoRequest
from app.api.delivery.services.service_cliente import ClienteService
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.utils.gerar_codigo_utils import gerar_codigo_telefone, validar_codigo_telefone
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/cliente", tags=["Cliente"])

@router.post("/novo-dispositivo", status_code=status.HTTP_200_OK)
def novo_dispositivo(data: NovoDispositivoRequest, db: Session = Depends(get_db)):
    service = ClienteService(db)
    cliente = service.repo.get_by_telefone(data.telefone)
    if not cliente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Telefone não cadastrado")
    gerar_codigo_telefone(data.telefone)
    return {"msg": "Código enviado"}

@router.post("/confirmar-codigo", response_model=ClienteOut)
def confirmar_codigo(data: ConfirmacaoCodigoRequest, db: Session = Depends(get_db)):
    if not validar_codigo_telefone(data.telefone, data.codigo):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código inválido ou expirado")
    service = ClienteService(db)
    cliente = service.repo.get_by_telefone(data.telefone)
    if not cliente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
    return ClienteOut.model_validate(cliente)

@router.post("/", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def create_new_cliente(data: ClienteCreate, db: Session = Depends(get_db)):
    logger.info("[Cliente] Create")
    service = ClienteService(db)
    cliente = service.create(data)

    # ✅ Garante que todos os campos do schema ClienteOut estejam presentes
    return ClienteOut.model_validate(cliente)

@router.get("/me", response_model=ClienteOut, status_code=status.HTTP_200_OK)
def read_current_cliente(cliente: "ClienteDeliveryModel" = Depends(get_cliente_by_super_token)):
    logger.info(f"[Cliente] Get current {cliente.telefone}")
    return ClienteOut.model_validate(cliente)


@router.put("/me", response_model=ClienteOut, status_code=status.HTTP_200_OK)
def update_current_cliente(
    data: ClienteUpdate,
    cliente: "ClienteDeliveryModel" = Depends(get_cliente_by_super_token),
    db: Session = Depends(get_db)
):
    logger.info(f"[Cliente] Update {cliente.telefone}")
    service = ClienteService(db)
    updated_cliente = service.update(cliente.super_token, data)

    # ✅ Retorna validado pelo schema
    return ClienteOut.model_validate(updated_cliente)
