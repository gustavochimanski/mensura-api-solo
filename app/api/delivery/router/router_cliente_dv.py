import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.api.delivery.models.model_cliente_codigo_validacao import ClienteOtpModel
from app.api.delivery.models.model_cliente_dv import ClienteDeliveryModel
from app.api.delivery.schemas.schema_cliente import ClienteOut, ClienteUpdate, ClienteCreate
from app.api.delivery.services.service_cliente import ClienteService
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/cliente", tags=["Cliente"])

@router.post("/novo-dispositivo")
def novo_dispositivo(telefone: str, db: Session = Depends(get_db)):
    cliente = db.query(ClienteDeliveryModel).filter_by(telefone=telefone).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Telefone não cadastrado")

    codigo = random.randint(100000, 999999)
    expira = datetime.utcnow() + timedelta(minutes=5)

    otp = ClienteOtpModel(telefone=telefone, codigo=codigo, expira_em=expira)
    db.add(otp)
    db.commit()

    # envia SMS real
    logger.info(telefone, f"Seu código de login é: {codigo}")

    return {"detail": "Código enviado com sucesso"}

@router.post("/confirmar-codigo")
def confirmar_codigo(telefone: str, codigo: str, db: Session = Depends(get_db)):
    otp = db.query(ClienteOtpModel).filter_by(telefone=telefone, codigo=codigo).first()
    if not otp or otp.expira_em < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Código inválido ou expirado")

    cliente = db.query(ClienteDeliveryModel).filter_by(telefone=telefone).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    db.delete(otp)  # remove o OTP usado
    db.commit()

    return {
        "id": cliente.id,
        "nome": cliente.nome,
        "telefone": cliente.telefone,
        "super_token": cliente.super_token,
    }

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
