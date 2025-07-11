# app/api/mensura/controllers/produtosDeliveryController.py
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    HTTPException,
    status,
    Query,
)
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.api.mensura.services.ProdutosDeliveryService import ProdutosDeliveryService
from app.database.db_connection import get_db
from app.api.mensura.schemas.delivery.produtos.produtosDelivery_schema import (
    ProdutosPaginadosResponse,
    CriarNovoProdutoResponse,
)
from app.utils.minio_client import upload_file_to_minio

produtosDeliveryRouter = APIRouter(tags=["Produtos - Delivery"])


@produtosDeliveryRouter.get(
    "/produtos/delivery",
    response_model=ProdutosPaginadosResponse
)
def listar_delivery(
    db: Session = Depends(get_db),
    cod_empresa: int = Query(1),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100)
):
    service = ProdutosDeliveryService(db)
    return service.listar_paginado(cod_empresa, page, limit)


@produtosDeliveryRouter.post(
    "/produtos/delivery",
    response_model=CriarNovoProdutoResponse,
    status_code=status.HTTP_201_CREATED
)
async def criar_produto(
    cod_barras: str = Form(...),
    descricao: str = Form(...),
    cod_categoria: int = Form(...),
    subcategoria_id: Optional[int] = Form(None),
    preco_venda: float = Form(...),
    custo: float = Form(...),
    data_cadastro: Optional[str] = Form(None),
    imagem: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    # Validação e upload de imagem
    imagem_url = None
    if imagem:
        if imagem.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(status_code=400, detail="Formato de imagem inválido")
        try:
            imagem_url = upload_file_to_minio(
                file=imagem,
                slug=cod_barras,
                bucket="produtos"
            )
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Monta o request DTO para o serviço
    # (note que o serviço espera um model Pydantic com esses campos)
    from app.api.mensura.schemas.delivery.produtos.produtosDelivery_schema import CriarNovoProdutoRequest

    produto_data = CriarNovoProdutoRequest(
        cod_barras=cod_barras,
        descricao=descricao,
        cod_categoria=cod_categoria,
        subcategoria_id=subcategoria_id,
        preco_venda=preco_venda,
        custo=custo,
        data_cadastro=datetime.fromisoformat(data_cadastro) if data_cadastro else None,
        imagem=imagem_url,
    )

    # Cria no serviço/repositório
    service = ProdutosDeliveryService(db)
    try:
        novo = service.criar_novo_produto(produto_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return novo


@produtosDeliveryRouter.delete(
    "/produtos/delivery/{cod_barras}",
    status_code=status.HTTP_204_NO_CONTENT
)
def deletar_produto(
    cod_barras: str,
    db: Session = Depends(get_db)
):
    service = ProdutosDeliveryService(db)
    service.deletar_produto(cod_barras)
    return None
