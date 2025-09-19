from typing import List

from fastapi import APIRouter, Depends, status, HTTPException, Path
from sqlalchemy.orm import Session

from app.api.mensura.models.user_model import UserModel
from app.api.delivery.repositories.repo_cliente import ClienteRepository
from app.api.delivery.schemas.schema_cliente import ClienteOut, ClienteAdminUpdate, ClienteUpdate
from app.api.delivery.schemas.schema_endereco import EnderecoOut
from app.api.delivery.services.service_cliente import ClienteService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/cliente/admin", tags=["Cliente - Admin"])

# ======================================================================
# ============================= ADMIN ==================================
# ======================================================================
@router.put("/update/{cliente_id}", response_model=ClienteOut, status_code=status.HTTP_200_OK)
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
    
    # Separar dados do cliente do endereço
    cliente_data = data.model_dump(exclude={'endereco'})
    endereco_data = data.endereco
    
    # Atualizar dados do cliente
    updated_cliente = service.update(cliente.super_token, ClienteUpdate(**cliente_data))
    
    # Processar ação de endereço se fornecida
    if endereco_data:
        from app.api.delivery.repositories.repo_endereco import EnderecoRepository
        from app.api.delivery.schemas.schema_endereco import EnderecoCreate, EnderecoUpdate
        
        endereco_repo = EnderecoRepository(db)
        
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

@router.get("/{cliente_id}/enderecos", response_model=List[EnderecoOut])
def get_enderecos_cliente(
    cliente_id: int = Path(..., description="ID do cliente para consultar endereços"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint para consultar endereços de um cliente específico.
    Requer autenticação de admin.
    """
    logger.info(f"[Cliente Admin] Consultar endereços - cliente_id={cliente_id} admin={current_user.id}")
    
    # Verifica se o cliente existe
    repo = ClienteRepository(db)
    cliente = repo.get_by_id(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Busca os endereços do cliente
    enderecos = repo.get_enderecos(cliente_id)
    
    # Converte para o schema de resposta
    return [EnderecoOut.model_validate(endereco) for endereco in enderecos]
