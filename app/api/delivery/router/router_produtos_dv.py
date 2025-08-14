# app/api/delivery/router/produtos_dv_router.py
from decimal import Decimal
from datetime import date
from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException, status, Query, Path, Body
from sqlalchemy.orm import Session
from typing import Optional

from pydantic import BaseModel

from app.database.db_connection import get_db
from app.api.delivery.services.service_produto_dv import ProdutosDeliveryService
from app.api.mensura.schemas.schema_produtos import (
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

# ---------- Endpoints ----------
@router.get("/search")
def search_produtos(
        db: Session = Depends(get_db),
        cod_empresa: int = Query(..., description="Empresa dona dos vínculos"),
        q: Optional[str] = Query(None, description="Termo de busca (descrição ou código de barras)"),
        page: int = Query(1, ge=1),
        limit: int = Query(30, ge=1, le=100),
        apenas_disponiveis: bool = Query(False, description="Somente ativos+disponíveis"),
):
  logger.info(
    f"[Produtos] Search - empresa={cod_empresa} q={q!r} page={page} limit={limit} disp={apenas_disponiveis}"
  )
  svc = ProdutosDeliveryService(db)
  return svc.buscar_paginado(
    empresa_id=cod_empresa,
    q=q,
    page=page,
    limit=limit,
    apenas_disponiveis=apenas_disponiveis,
  )


@router.put("/produtos/{cod_barras}", response_model=CriarNovoProdutoResponse)
async def atualizar_produto(
  cod_empresa: int = Form(...),
  cod_barras: str = Path(...),
  descricao: str = Form(...),
  cod_categoria: int = Form(...),
  vitrine_id: Optional[int] = Form(None),
  preco_venda: Decimal = Form(...),
  custo: Optional[Decimal] = Form(None),
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
    cod_categoria=cod_categoria,
    vitrine_id=vitrine_id,
    preco_venda=preco_venda,
    custo=custo,
    data_cadastro=parsed_date,
    imagem=imagem_url,
  )
  service = ProdutosDeliveryService(db)
  try:
    return service.atualizar_produto(cod_empresa, cod_barras, dto)
  except HTTPException:
    raise
  except IntegrityError:
    db.rollback()
    raise HTTPException(400, detail="Erro de integridade nos dados")

@router.patch("/produtos/{cod_barras}/disponibilidade", status_code=status.HTTP_204_NO_CONTENT)
def set_disponibilidade(
  cod_barras: str,
  payload: SetDisponibilidadeRequest = Body(...),
  db: Session = Depends(get_db)
):
  logger.info(f"[Produtos] Disponibilidade - {cod_barras} / empresa {payload.empresa_id} -> {payload.disponivel}")
  service = ProdutosDeliveryService(db)
  service.set_disponibilidade(
    empresa_id=payload.empresa_id,
    cod_barras=cod_barras,
    on=payload.disponivel
  )
  return None

@router.delete("/produtos/{cod_barras}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_produto(
  cod_barras: str,
  empresa_id: int = Query(..., description="Empresa dona do vínculo a ser removido"),
  db: Session = Depends(get_db)
):
  logger.info(f"[Produtos] Deletar - {cod_barras} / empresa {empresa_id}")
  service = ProdutosDeliveryService(db)
  service.deletar_produto(empresa_id, cod_barras)
  return None
