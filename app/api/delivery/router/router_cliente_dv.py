import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.delivery.models.model_cliente_codigo_validacao import ClienteOtpModel
from app.api.delivery.models.model_cliente_dv import ClienteDeliveryModel
from app.api.delivery.repositories.repo_cliente import ClienteRepository
from app.api.delivery.schemas.schema_cliente import ClienteOut, ClienteUpdate, ClienteCreate, ClienteAdminUpdate
from app.api.delivery.services.service_cliente import ClienteService
from app.core.client_dependecies import get_cliente_by_super_token
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/cliente", tags=["Cliente"])

class NovoDispositivoRequest(BaseModel):
    telefone: str

# ======================================================================
# ============================ CLIENTE =================================
# ======================================================================
@router.post("/novo-dispositivo")
def novo_dispositivo(body: NovoDispositivoRequest, db: Session = Depends(get_db)):
    telefone = body.telefone
    cliente = db.query(ClienteDeliveryModel).filter_by(telefone=telefone).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Telefone não cadastrado")

    codigo = random.randint(100000, 999999)
    expira = datetime.utcnow() + timedelta(minutes=5)

    otp = ClienteOtpModel(telefone=telefone, codigo=codigo, expira_em=expira)
    db.add(otp)
    db.commit()

    # envia SMS real
    logger.info(f"Seu código de login é: {codigo}")

    return {"detail": "Código enviado com sucesso"}


class ConfirmacaoCodigoRequest(BaseModel):
    telefone: str
    codigo: str

@router.post("/confirmar-codigo")
def confirmar_codigo(body: ConfirmacaoCodigoRequest, db: Session = Depends(get_db)):
    otp = db.query(ClienteOtpModel).filter_by(telefone=body.telefone, codigo=body.codigo).first()
    if not otp or otp.expira_em < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Código inválido ou expirado")

    cliente = db.query(ClienteDeliveryModel).filter_by(telefone=body.telefone).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    db.delete(otp)  # remove o OTP usado
    db.commit()

    return {
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
def read_current_cliente(cliente: ClienteDeliveryModel = Depends(get_cliente_by_super_token)):
    logger.info(f"[Cliente] Get current {cliente.telefone}")

    if not cliente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")

    return ClienteOut.model_validate(cliente)



@router.put("/me", response_model=ClienteOut, status_code=status.HTTP_200_OK)
def update_current_cliente(
    data: ClienteUpdate,
    cliente: ClienteDeliveryModel = Depends(get_cliente_by_super_token),
    db: Session = Depends(get_db)
):
    logger.info(f"[Cliente] Update {cliente.telefone}")

    if not cliente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")

    service = ClienteService(db)
    updated_cliente = service.update(cliente.super_token, data)

    return ClienteOut.model_validate(updated_cliente)




# ======================================================================
# ============================= ADMIN ==================================
# ======================================================================
@router.put("/admin-update/{cliente_id}", response_model=ClienteOut, status_code=status.HTTP_200_OK)
def update_cliente_admin(
    cliente_id: int,
    data: ClienteAdminUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"[Cliente Admin] Update ID {cliente_id} by user {current_user.id}")

    repo = ClienteRepository(db)
    cliente = repo.get_by_id(cliente_id)
    if not cliente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")

    service = ClienteService(db)
    
    # Separar dados do cliente dos endereços
    cliente_data = data.model_dump(exclude={'enderecos'})
    enderecos_data = data.enderecos or []
    
    # Atualizar dados do cliente
    updated_cliente = service.update(cliente.super_token, ClienteUpdate(**cliente_data))
    
    # Processar ações de endereços se fornecidas
    if enderecos_data:
        from app.api.delivery.repositories.repo_endereco import EnderecoRepository
        from app.api.delivery.schemas.schema_endereco import EnderecoCreate, EnderecoUpdate
        
        endereco_repo = EnderecoRepository(db)
        
        for endereco_data in enderecos_data:
            acao = endereco_data.acao
            endereco_id = endereco_data.id
            
            if acao == "add":
                # Adicionar novo endereço
                endereco_dict = endereco_data.model_dump(exclude={'acao', 'id'})
                # Remove campos None para não enviar dados vazios
                endereco_dict = {k: v for k, v in endereco_dict.items() if v is not None}
                endereco_repo.create(cliente_id, EnderecoCreate(**endereco_dict))
                logger.info(f"[Cliente Admin] Endereço adicionado para cliente {cliente_id}")
                
            elif acao == "update":
                # Atualizar endereço existente
                if not endereco_id:
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST, 
                        "ID do endereço é obrigatório para atualização"
                    )
                
                endereco_dict = endereco_data.model_dump(exclude={'acao', 'id'})
                # Remove campos None para não sobrescrever com None
                endereco_dict = {k: v for k, v in endereco_dict.items() if v is not None}
                
                if endereco_dict:  # Só atualiza se houver dados para atualizar
                    endereco_repo.update(cliente_id, endereco_id, EnderecoUpdate(**endereco_dict))
                    logger.info(f"[Cliente Admin] Endereço {endereco_id} atualizado para cliente {cliente_id}")
                
            elif acao == "remove":
                # Remover endereço
                if not endereco_id:
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST, 
                        "ID do endereço é obrigatório para remoção"
                    )
                
                endereco_repo.delete(cliente_id, endereco_id)
                logger.info(f"[Cliente Admin] Endereço {endereco_id} removido do cliente {cliente_id}")

    return ClienteOut.model_validate(updated_cliente)
