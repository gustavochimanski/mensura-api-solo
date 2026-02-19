# app/api/chatbot/router/router_carrinho.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database.db_connection import get_db
from app.api.chatbot.services.service_carrinho import CarrinhoService
from app.api.chatbot.schemas.schema_carrinho import (
    CriarCarrinhoRequest,
    AdicionarItemCarrinhoRequest,
    AtualizarItemCarrinhoRequest,
    RemoverItemCarrinhoRequest,
    CarrinhoResponse,
    CarrinhoResumoResponse,
)
from app.api.catalogo.adapters.produto_adapter import ProdutoAdapter
from app.api.catalogo.adapters.complemento_adapter import ComplementoAdapter
from app.api.catalogo.adapters.receitas_adapter import ReceitasAdapter
from app.api.catalogo.adapters.combo_adapter import ComboAdapter
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.catalogo.contracts.complemento_contract import IComplementoContract
from app.api.catalogo.contracts.receitas_contract import IReceitasContract
from app.api.catalogo.contracts.combo_contract import IComboContract
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/chatbot/carrinho",
    tags=["API - Chatbot - Carrinho"]
)


def get_carrinho_service(db: Session = Depends(get_db)) -> CarrinhoService:
    """Dependency para obter serviço de carrinho com contratos"""
    produto_contract: IProdutoContract = ProdutoAdapter(db)
    complemento_contract: IComplementoContract = ComplementoAdapter(db)
    receitas_contract: IReceitasContract = ReceitasAdapter(db)
    combo_contract: IComboContract = ComboAdapter(db)
    
    return CarrinhoService(
        db=db,
        produto_contract=produto_contract,
        complemento_contract=complemento_contract,
        receitas_contract=receitas_contract,
        combo_contract=combo_contract,
    )


@router.post("/", response_model=CarrinhoResponse, status_code=status.HTTP_201_CREATED)
async def criar_carrinho(
    data: CriarCarrinhoRequest,
    service: CarrinhoService = Depends(get_carrinho_service)
):
    """Cria ou atualiza carrinho temporário do chatbot"""
    try:
        return service.criar_ou_atualizar_carrinho(data)
    except Exception as e:
        logger.error(f"[Carrinho] Erro ao criar carrinho: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar carrinho: {str(e)}"
        )


@router.get("/{user_id}", response_model=Optional[CarrinhoResponse])
async def obter_carrinho(
    user_id: str,
    empresa_id: Optional[int] = None,
    service: CarrinhoService = Depends(get_carrinho_service)
):
    """Obtém carrinho do usuário"""
    carrinho = service.obter_carrinho(user_id, empresa_id)
    if not carrinho:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrinho não encontrado"
        )
    return carrinho


@router.post("/adicionar-item", response_model=CarrinhoResponse)
async def adicionar_item(
    data: AdicionarItemCarrinhoRequest,
    service: CarrinhoService = Depends(get_carrinho_service)
):
    """Adiciona item ao carrinho"""
    try:
        return service.adicionar_item(data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Carrinho] Erro ao adicionar item: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao adicionar item: {str(e)}"
        )


@router.put("/atualizar-item", response_model=CarrinhoResponse)
async def atualizar_item(
    user_id: str,
    data: AtualizarItemCarrinhoRequest,
    service: CarrinhoService = Depends(get_carrinho_service)
):
    """Atualiza item do carrinho"""
    try:
        return service.atualizar_item(user_id, data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Carrinho] Erro ao atualizar item: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar item: {str(e)}"
        )


@router.delete("/remover-item", response_model=CarrinhoResponse)
async def remover_item(
    user_id: str,
    data: RemoverItemCarrinhoRequest,
    service: CarrinhoService = Depends(get_carrinho_service)
):
    """Remove item do carrinho"""
    try:
        return service.remover_item(user_id, data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Carrinho] Erro ao remover item: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao remover item: {str(e)}"
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def limpar_carrinho(
    user_id: str,
    empresa_id: Optional[int] = None,
    service: CarrinhoService = Depends(get_carrinho_service)
):
    """Limpa o carrinho do usuário"""
    deleted = service.limpar_carrinho(user_id, empresa_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrinho não encontrado"
        )
