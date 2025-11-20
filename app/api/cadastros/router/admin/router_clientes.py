from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.api.cadastros.models.user_model import UserModel
from app.api.cadastros.repositories.repo_cliente import ClienteRepository
from app.api.cadastros.schemas.schema_cliente import ClienteOut, ClienteAdminUpdate, ClienteUpdate, ClienteCreate
from app.api.cardapio.schemas.schema_endereco import EnderecoOut, EnderecoCreate
from app.api.cadastros.services.service_cliente import ClienteService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/cadastros/admin/clientes", tags=["Admin - Cadastros - Clientes"])

# ======================================================================
# ============================= ADMIN ==================================
# ======================================================================

@router.get("/", response_model=List[ClienteOut], status_code=status.HTTP_200_OK)
def listar_clientes(
    ativo: Optional[bool] = Query(None, description="Filtrar por status ativo/inativo"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint para listar todos os clientes.
    Requer autenticação de admin.
    """
    logger.info(f"[Cliente Admin] Listar clientes - admin={current_user.id}, ativo={ativo}")
    
    repo = ClienteRepository(db)
    clientes = repo.list(ativo=ativo)
    
    return [ClienteOut.model_validate(cliente) for cliente in clientes]

@router.get("/{cliente_id}", response_model=ClienteOut, status_code=status.HTTP_200_OK)
def get_cliente(
    cliente_id: int = Path(..., description="ID do cliente"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint para obter um cliente específico por ID.
    Requer autenticação de admin.
    """
    logger.info(f"[Cliente Admin] Get cliente ID {cliente_id} by user {current_user.id}")
    
    repo = ClienteRepository(db)
    cliente = repo.get_by_id(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    return ClienteOut.model_validate(cliente)

@router.post("/", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def criar_cliente(
    data: ClienteCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint para criar um novo cliente.
    Requer autenticação de admin.
    """
    logger.info(f"[Cliente Admin] Criar cliente by user {current_user.id}")
    
    service = ClienteService(db)
    
    # Verificar se telefone já existe
    repo = ClienteRepository(db)
    if repo.get_by_telefone(data.telefone):
        raise HTTPException(
            status_code=400, 
            detail="Telefone já cadastrado"
        )
    
    # Verificar se email já existe (se fornecido)
    if data.email and repo.get_by_email(data.email):
        raise HTTPException(
            status_code=400, 
            detail="Email já cadastrado"
        )
    
    # Verificar se CPF já existe (se fornecido)
    if data.cpf and repo.get_by_cpf(data.cpf):
        raise HTTPException(
            status_code=400, 
            detail="CPF já cadastrado"
        )
    
    # Criar cliente
    novo_cliente = service.create(data)
    logger.info(f"[Cliente Admin] Cliente criado com ID {novo_cliente.id}")
    
    return ClienteOut.model_validate(novo_cliente)

@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_cliente(
    cliente_id: int = Path(..., description="ID do cliente"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint para deletar um cliente.
    Requer autenticação de admin.
    """
    logger.info(f"[Cliente Admin] Deletar cliente ID {cliente_id} by user {current_user.id}")
    
    repo = ClienteRepository(db)
    cliente = repo.get_by_id(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Verificar se cliente tem pedidos
    from app.api.cardapio.repositories.repo_pedidos import PedidoRepository
    pedido_repo = PedidoRepository(db)
    pedidos = pedido_repo.get_by_cliente_id(cliente_id)
    if pedidos:
        raise HTTPException(
            status_code=400,
            detail="Não é possível deletar cliente com pedidos associados"
        )
    
    # Deletar endereços do cliente primeiro
    from app.api.cadastros.repositories.repo_endereco import EnderecoRepository
    endereco_repo = EnderecoRepository(db)
    enderecos = repo.get_enderecos(cliente_id)
    for endereco in enderecos:
        endereco_repo.delete(cliente_id, endereco.id)
    
    # Deletar cliente
    db.delete(cliente)
    db.commit()
    
    logger.info(f"[Cliente Admin] Cliente {cliente_id} deletado com sucesso")
    
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
        from app.api.cadastros.repositories.repo_endereco import EnderecoRepository
        from app.api.cardapio.schemas.schema_endereco import EnderecoCreate, EnderecoUpdate
        
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

@router.post("/{cliente_id}/criar-endereco", response_model=EnderecoOut, status_code=status.HTTP_201_CREATED)
def criar_endereco_cliente(
    cliente_id: int = Path(..., description="ID do cliente para adicionar endereço"),
    data: EnderecoCreate = ...,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint para criar um novo endereço para um cliente específico.
    Requer autenticação de admin.
    """
    logger.info(f"[Cliente Admin] Criar endereço - cliente_id={cliente_id} admin={current_user.id}")
    
    # Verifica se o cliente existe
    repo = ClienteRepository(db)
    cliente = repo.get_by_id(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Verifica se o endereço já existe para este cliente
    from app.api.cadastros.repositories.repo_endereco import EnderecoRepository
    endereco_repo = EnderecoRepository(db)
    
    if endereco_repo.endereco_existe(cliente_id, data):
        raise HTTPException(
            status_code=400,
            detail="Endereço já cadastrado para este cliente"
        )
    
    # Se este endereço for marcado como principal, remove a marcação dos outros
    if data.is_principal:
        from app.api.cadastros.models.model_endereco_dv import EnderecoModel
        endereco_repo.db.query(EnderecoModel).filter(
            EnderecoModel.cliente_id == cliente_id
        ).update({"is_principal": False})
    
    # Cria o novo endereço
    novo_endereco = endereco_repo.create(cliente_id, data)
    logger.info(f"[Cliente Admin] Endereço criado com ID {novo_endereco.id} para cliente {cliente_id}")
    
    return EnderecoOut.model_validate(novo_endereco)

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
