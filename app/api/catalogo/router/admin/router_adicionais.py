from typing import List, Optional
from fastapi import APIRouter, Body, Depends, status, Path, Query, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.api.catalogo.schemas.schema_complemento import (
    AdicionalResponse,
    CriarItemRequest,
    AtualizarAdicionalRequest,
)
from app.api.catalogo.services.service_complemento import ComplementoService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger
from app.utils.minio_client import update_file_to_minio

router = APIRouter(
    prefix="/api/catalogo/admin/adicionais",
    tags=["Admin - Catalogo - Adicionais"],
    dependencies=[Depends(get_current_user)]
)


# ------ CRUD de Adicionais (Independentes) ------
@router.post("/", response_model=AdicionalResponse, status_code=status.HTTP_201_CREATED)
def criar_adicional(
    req: CriarItemRequest,
    db: Session = Depends(get_db),
):
    """Cria um adicional independente (pode ser usado em complementos, receitas, combos, etc.)."""
    logger.info(f"[Adicionais] Criar - empresa={req.empresa_id} nome={req.nome}")
    service = ComplementoService(db)
    return service.criar_item(req)


@router.get("/", response_model=List[AdicionalResponse])
def listar_adicionais(
    empresa_id: int = Query(..., description="ID da empresa"),
    apenas_ativos: bool = Query(True, description="Apenas adicionais ativos"),
    search: Optional[str] = Query(None, description="Termo de busca (nome ou descrição)"),
    db: Session = Depends(get_db),
):
    """
    Lista todos os adicionais de uma empresa.
    
    - Sem `search`: retorna todos os adicionais (respeitando `apenas_ativos`).
    - Com `search`: busca por nome/descrição contendo o termo (case-insensitive).
    """
    service = ComplementoService(db)
    if search and search.strip():
        logger.info(f"[Adicionais] Buscar - empresa={empresa_id} search={search} apenas_ativos={apenas_ativos}")
        return service.buscar_adicionais(empresa_id, search, apenas_ativos)

    logger.info(f"[Adicionais] Listar - empresa={empresa_id} apenas_ativos={apenas_ativos}")
    return service.listar_itens(empresa_id, apenas_ativos)


@router.get("/{adicional_id}", response_model=AdicionalResponse)
def buscar_adicional(
    adicional_id: int = Path(..., description="ID do adicional"),
    db: Session = Depends(get_db),
):
    """Busca um adicional por ID."""
    logger.info(f"[Adicionais] Buscar - id={adicional_id}")
    service = ComplementoService(db)
    return service.buscar_item_por_id(adicional_id)


@router.put("/{adicional_id}", response_model=AdicionalResponse)
def atualizar_adicional(
    adicional_id: int = Path(..., description="ID do adicional"),
    req: AtualizarAdicionalRequest = Body(...),
    db: Session = Depends(get_db),
):
    """Atualiza um adicional existente."""
    logger.info(f"[Adicionais] Atualizar - id={adicional_id}")
    service = ComplementoService(db)
    return service.atualizar_item(adicional_id, req)


@router.delete("/{adicional_id}", status_code=status.HTTP_200_OK)
def deletar_adicional(
    adicional_id: int = Path(..., description="ID do adicional"),
    db: Session = Depends(get_db),
):
    """Deleta um adicional (remove automaticamente os vínculos com complementos, receitas, etc.)."""
    logger.info(f"[Adicionais] Deletar - id={adicional_id}")
    service = ComplementoService(db)
    service.deletar_item(adicional_id)
    return {"message": "Adicional deletado com sucesso"}


@router.put("/{adicional_id}/imagem", response_model=AdicionalResponse, status_code=status.HTTP_200_OK)
async def atualizar_imagem_adicional(
    adicional_id: int = Path(..., description="ID do adicional (item)"),
    cod_empresa: int = Form(..., description="ID da empresa dona do adicional"),
    imagem: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Faz upload/atualização da imagem do adicional (item) no MinIO e salva a URL pública no campo `imagem`.

    - Envia como `multipart/form-data`
    - Campos: `cod_empresa` e `imagem`
    """
    if imagem.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Formato de imagem inválido")

    service = ComplementoService(db)
    item = service.repo_item.buscar_por_id(adicional_id)
    if not item:
        raise HTTPException(status_code=404, detail="Adicional não encontrado.")

    if int(getattr(item, "empresa_id", 0) or 0) != int(cod_empresa):
        raise HTTPException(status_code=400, detail="cod_empresa não confere com a empresa do adicional.")

    try:
        nova_url = update_file_to_minio(
            db=db,
            cod_empresa=cod_empresa,
            file=imagem,
            slug="adicionais",
            url_antiga=getattr(item, "imagem", None),
        )
    except Exception as e:
        logger.error(f"[Adicionais] Erro upload imagem - id={adicional_id} empresa={cod_empresa}: {e}")
        raise HTTPException(status_code=500, detail="Erro ao fazer upload da imagem")

    service.repo_item.atualizar_item(item, imagem=nova_url)
    db.commit()
    db.refresh(item)
    return service.buscar_item_por_id(adicional_id)

