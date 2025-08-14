# app/api/delivery/router/produtos_dv_router.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.mensura.schemas.schema_produtos import ProdutosPaginadosResponse
from app.api.mensura.services.service_produto import ProdutosMensuraService
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery", tags=["Produtos - Delivery"])
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