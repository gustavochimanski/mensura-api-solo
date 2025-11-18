from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session
from typing import List

from app.api.cadastros.models.user_model import UserModel
from app.api.cadastros.services.service_endereco import EnderecosService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.cardapio.schemas.schema_endereco import EnderecoOut, EnderecoCreate, EnderecoUpdate
from app.utils.logger import logger

router = APIRouter(prefix="/api/cadastros/admin/enderecos", 
    tags=["Admin - Cadastros - Endereços"],
    dependencies=[Depends(get_current_user)]
)

# ======================================================================
# ============================= ADMIN ==================================
# ======================================================================

@router.get("/cliente/{cliente_id}", response_model=List[EnderecoOut])
def listar_enderecos_admin(
    cliente_id: int = Path(..., description="ID do cliente para listar endereços"),
    db: Session = Depends(get_db)
):
    """
    Endpoint para admin listar endereços de um cliente específico.
    Requer autenticação de admin.
    """
    svc = EnderecosService(db)
    return svc.list_by_cliente_id(cliente_id)

@router.post("/cliente/{cliente_id}", response_model=EnderecoOut, status_code=status.HTTP_201_CREATED)
def criar_endereco_admin(
    cliente_id: int = Path(..., description="ID do cliente para criar endereço"),
    payload: EnderecoCreate = ...,
    db: Session = Depends(get_db)
):
    """
    Endpoint para admin criar endereço para um cliente específico.
    Verifica se o endereço já existe antes de criar.
    Requer autenticação de admin.
    """
    svc = EnderecosService(db)
    return svc.create_by_cliente_id(cliente_id, payload)

@router.put("/cliente/{cliente_id}/endereco/{endereco_id}", response_model=EnderecoOut)
def atualizar_endereco_admin(
    cliente_id: int = Path(..., description="ID do cliente"),
    endereco_id: int = Path(..., description="ID do endereço para atualizar"),
    payload: EnderecoUpdate = ...,
    db: Session = Depends(get_db)
):
    """
    Endpoint para admin atualizar endereço de um cliente específico.
    Verifica se o endereço já existe antes de atualizar.
    Verifica se o endereço está sendo usado em pedidos ativos.
    Requer autenticação de admin.
    """
    svc = EnderecosService(db)
    return svc.update_by_cliente_id(cliente_id, endereco_id, payload)
