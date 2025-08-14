# app/api/delivery/router/produtos_dv_router.py
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, Form, File, HTTPException
from rich import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.mensura.schemas.schema_produtos import ProdutosPaginadosResponse, CriarNovoProdutoResponse, \
    CriarNovoProdutoRequest
from app.api.mensura.services.service_produto import ProdutosMensuraService
from app.database.db_connection import get_db
from app.utils.logger import logger
from app.utils.minio_client import upload_file_to_minio

router = APIRouter(prefix="/api/mensura", tags=["Produtos - Delivery"])
@router.get(path="/produtos", response_model=ProdutosPaginadosResponse, summary="Lista produtos ERP", description="Retorna produtos com todas as colunas inclusas para exibição")
def listar_delivery(
  db: Session = Depends(get_db),
  cod_empresa: int = Query(...),
  page: int = Query(1, ge=1),
  limit: int = Query(30, ge=1, le=100),
  apenas_disponiveis: bool = Query(False),
):
  logger.info(f"[Produtos] Listar - empresa={cod_empresa} page={page} limit={limit} disp={apenas_disponiveis}")
  service = ProdutosMensuraService(db)
  return service.listar_paginado(cod_empresa, page, limit, apenas_disponiveis=apenas_disponiveis)


@router.post("/produtos", response_model=CriarNovoProdutoResponse, status_code=status.HTTP_201_CREATED)
async def criar_produto(
  cod_empresa: int = Form(...),
  cod_barras: str = Form(...),
  descricao: str = Form(...),
  preco_venda: Decimal = Form(...),
  custo: Optional[Decimal] = Form(None),
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
      imagem_url = upload_file_to_minio(db, cod_empresa, imagem, "produtos")
    except RuntimeError as e:
      raise HTTPException(status_code=500, detail=str(e))

  parsed_date = None
  if data_cadastro:
    try:
      parsed_date = date.fromisoformat(data_cadastro)
    except ValueError:
      raise HTTPException(400, detail="data_cadastro inválida (use YYYY-MM-DD)")

  dto = CriarNovoProdutoRequest(
    empresa_id=cod_empresa,
    cod_barras=cod_barras,
    descricao=descricao,
    preco_venda=preco_venda,
    custo=custo,
    data_cadastro=parsed_date,
    imagem=imagem_url,
  )

  service = ProdutosMensuraService(db)
  try:
    return service.criar_novo_produto(cod_empresa, dto)
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
  except IntegrityError:
    db.rollback()
    raise HTTPException(400, detail="Erro de integridade nos dados")
