from decimal import Decimal

from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException, status, Query, Path, Body
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.database.db_connection import get_db
from app.api.delivery.services.produtos_service import ProdutosDeliveryService
from app.api.delivery.schemas.produtos.produtos_dv_schema import (
    ProdutosPaginadosResponse,
    CriarNovoProdutoResponse,
    CriarNovoProdutoRequest
)
from app.utils.minio_client import upload_file_to_minio
from app.utils.logger import logger
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/api/delivery", tags=["Produtos - Delivery"])

class SetDisponibilidadeRequest(BaseModel):
    empresa_id: int
    disponivel: bool

@router.get("/produtos/delivery", response_model=ProdutosPaginadosResponse)
def listar_delivery(
    db: Session = Depends(get_db),
    cod_empresa: int = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    apenas_disponiveis: bool = Query(False),
):
    logger.info(f"[Produtos] Listar - empresa={cod_empresa} page={page} limit={limit} disp={apenas_disponiveis}")
    service = ProdutosDeliveryService(db)
    return service.listar_paginado(cod_empresa, page, limit, apenas_disponiveis=apenas_disponiveis)

@router.post("/produtos/delivery", response_model=CriarNovoProdutoResponse, status_code=status.HTTP_201_CREATED)
async def criar_produto(
    cod_empresa: int = Form(...),
    cod_barras: str = Form(...),
    descricao: str = Form(...),
    cod_categoria: int = Form(...),
    vitrine_id: Optional[int] = Form(None),
    preco_venda: Decimal = Form(...),
    custo: Decimal = Form(...),
    data_cadastro: Optional[str] = Form(None),
    imagem: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    logger.info(f"[Produtos] Criar - {cod_barras} / empresa {cod_empresa}")
    imagem_url = None
    if imagem:
        if imagem.content_type not in {"image/jpeg","image/png","image/webp"}:
            raise HTTPException(status_code=400, detail="Formato de imagem inválido")
        try:
            imagem_url = upload_file_to_minio(db, cod_empresa,  imagem, "produtos")
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))

    dto = CriarNovoProdutoRequest(
        empresa_id=cod_empresa,
        cod_barras=cod_barras,
        descricao=descricao,
        cod_categoria=cod_categoria,
        vitrine_id=vitrine_id,
        preco_venda=preco_venda,
        custo=custo,
        data_cadastro=datetime.fromisoformat(data_cadastro) if data_cadastro else None,
        imagem=imagem_url,
    )

    service = ProdutosDeliveryService(db)
    try:
        return service.criar_novo_produto(cod_empresa, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError as ie:
        db.rollback()
        raise HTTPException(400, detail="Erro de integridade nos dados")

@router.put("/produtos/delivery/{cod_barras}", response_model=CriarNovoProdutoResponse)
async def atualizar_produto(
    cod_empresa: int = Form(...),
    cod_barras: str = Path(...),
    descricao: str = Form(...),
    cod_categoria: int = Form(...),
    subcategoria_id: Optional[int] = Form(None),
    preco_venda: float = Form(...),
    custo: float = Form(...),
    data_cadastro: Optional[str] = Form(None),
    imagem: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    logger.info(f"[Produtos] Atualizar - {cod_barras} / empresa {cod_empresa}")
    imagem_url = None
    if imagem:
        if imagem.content_type not in {"image/jpeg","image/png","image/webp"}:
            raise HTTPException(status_code=400, detail="Formato de imagem inválido")
        try:
            imagem_url = upload_file_to_minio(db, cod_empresa,  imagem, "produtos")
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))

    dto = CriarNovoProdutoRequest(
        cod_barras=cod_barras,
        descricao=descricao,
        cod_categoria=cod_categoria,
        subcategoria_id=subcategoria_id,
        preco_venda=preco_venda,
        custo=custo,
        data_cadastro=datetime.fromisoformat(data_cadastro) if data_cadastro else None,
        imagem=imagem_url,
    )
    service = ProdutosDeliveryService(db)
    try:
        return service.atualizar_produto(cod_barras, dto)
    except HTTPException:
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, detail="Erro de integridade nos dados")

@router.patch("/produtos/delivery/{cod_barras}/disponibilidade", status_code=status.HTTP_204_NO_CONTENT)
def set_disponibilidade(
    cod_barras: str,
    payload: SetDisponibilidadeRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    Liga/desliga disponibilidade do produto (empresa x produto).
    """
    logger.info(f"[Produtos] Disponibilidade - {cod_barras} / empresa {payload.empresa_id} -> {payload.disponivel}")
    service = ProdutosDeliveryService(db)
    service.set_disponibilidade(
        cod_barras=cod_barras,
        empresa_id=payload.empresa_id,
        on=payload.disponivel
    )
    return None

@router.delete("/produtos/delivery/{cod_barras}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_produto(cod_barras: str, db: Session = Depends(get_db)):
    logger.info(f"[Produtos] Deletar - {cod_barras}")
    service = ProdutosDeliveryService(db)
    service.__delattr__(cod_barras)
    return None
