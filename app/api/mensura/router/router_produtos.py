# app/api/delivery/router/produtos_dv_router.py
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, Form, File, HTTPException
from pydantic import BaseModel
from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.mensura.schemas.schema_produtos import ProdutosPaginadosResponse, CriarNovoProdutoResponse, \
    CriarNovoProdutoRequest, AtualizarProdutoRequest
from app.api.mensura.services.service_produto import ProdutosMensuraService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger
from app.utils.minio_client import upload_file_to_minio

router = APIRouter(prefix="/api/mensura/admin/produtos", tags=["Admin - Mensura - Produtos"], dependencies=[Depends(get_current_user)])
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
  svc = ProdutosMensuraService(db)
  return svc.buscar_paginado(
    empresa_id=cod_empresa,
    q=q,
    page=page,
    limit=limit,
    apenas_disponiveis=apenas_disponiveis,
  )


@router.get(path="/", response_model=ProdutosPaginadosResponse, summary="Lista produtos ERP", description="Retorna produtos com todas as colunas inclusas para exibição")
def listar_delivery(
  db: Session = Depends(get_db),
  cod_empresa: int = Query(...),
  page: int = Query(1, ge=1),
  limit: int = Query(30, ge=1, le=100),
  apenas_disponiveis: bool = Query(False),
  search: Optional[str] = Query(None, description="Termo de busca (código de barras, descrição ou SKU)"),
):
  logger.info(f"[Produtos] Listar - empresa={cod_empresa} page={page} limit={limit} disp={apenas_disponiveis} search={search}")
  service = ProdutosMensuraService(db)
  
  if search:
    return service.buscar_produtos(cod_empresa, search, page, limit, apenas_disponiveis=apenas_disponiveis)
  else:
    return service.listar_paginado(cod_empresa, page, limit, apenas_disponiveis=apenas_disponiveis)


@router.post("/", response_model=CriarNovoProdutoResponse)
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


@router.put("/{cod_barras}", response_model=CriarNovoProdutoResponse)
async def atualizar_produto(
  cod_barras: str,
  cod_empresa: int = Form(...),
  descricao: Optional[str] = Form(None),
  preco_venda: Optional[Decimal] = Form(None),
  custo: Optional[Decimal] = Form(None),
  sku_empresa: Optional[str] = Form(None),
  disponivel: Optional[bool] = Form(None),
  exibir_delivery: Optional[bool] = Form(None),
  ativo: Optional[bool] = Form(None),
  unidade_medida: Optional[str] = Form(None),
  imagem: Optional[UploadFile] = File(None),
  db: Session = Depends(get_db),
):
  logger.info(f"[Produtos] Atualizar - {cod_barras} / empresa {cod_empresa}")
  
  # processa upload de imagem se fornecido
  imagem_url = None
  if imagem:
    if imagem.content_type not in {"image/jpeg","image/png","image/webp"}:
      raise HTTPException(status_code=400, detail="Formato de imagem inválido")
    try:
      imagem_url = upload_file_to_minio(db, cod_empresa, imagem, "produtos")
    except RuntimeError as e:
      raise HTTPException(status_code=500, detail=str(e))

  # valida se pelo menos um campo foi fornecido para atualização
  campos_fornecidos = any([
    descricao is not None,
    preco_venda is not None,
    custo is not None,
    sku_empresa is not None,
    disponivel is not None,
    exibir_delivery is not None,
    ativo is not None,
    unidade_medida is not None,
    imagem_url is not None
  ])
  
  if not campos_fornecidos:
    raise HTTPException(status_code=400, detail="Pelo menos um campo deve ser fornecido para atualização")

  dto = AtualizarProdutoRequest(
    descricao=descricao,
    preco_venda=preco_venda,
    custo=custo,
    sku_empresa=sku_empresa,
    disponivel=disponivel,
    exibir_delivery=exibir_delivery,
    ativo=ativo,
    unidade_medida=unidade_medida,
    imagem=imagem_url,
  )

  service = ProdutosMensuraService(db)
  try:
    return service.atualizar_produto(cod_empresa, cod_barras, dto)
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
  except HTTPException:
    raise
  except Exception as e:
    db.rollback()
    logger.error(f"Erro ao atualizar produto {cod_barras}: {str(e)}")
    raise HTTPException(status_code=500, detail="Erro interno do servidor")


@router.delete("/{cod_barras}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_produto(
  cod_barras: str,
  empresa_id: int = Query(..., description="Empresa dona do vínculo a ser removido"),
  db: Session = Depends(get_db)
):
  logger.info(f"[Produtos] Deletar - {cod_barras} / empresa {empresa_id}")
  service = ProdutosMensuraService(db)
  service.deletar_produto(empresa_id, cod_barras)
  return None