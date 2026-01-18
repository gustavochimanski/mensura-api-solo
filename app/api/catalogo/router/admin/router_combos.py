from fastapi import APIRouter, Depends, Query, Path, HTTPException
from fastapi import status, UploadFile, Form, File
from sqlalchemy.orm import Session
import json
from typing import Optional

from app.api.catalogo.schemas.schema_combo import (
    CriarComboRequest,
    AtualizarComboRequest,
    ListaCombosResponse,
    ComboDTO,
)
from app.api.catalogo.services.service_combo import CombosService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger
from app.utils.minio_client import update_file_to_minio


router = APIRouter(prefix="/api/catalogo/admin/combos", tags=["Admin - Catalogo - Combos"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=ListaCombosResponse)
def listar_combos(
    cod_empresa: int = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    search: Optional[str] = Query(None, description="Termo de busca no título/descrição do combo"),
    db: Session = Depends(get_db),
):
    """
    Lista combos de uma empresa com paginação e busca opcional.

    - `search`: termo aplicado em título/descrição (case-insensitive).
    """
    svc = CombosService(db)
    return svc.listar(cod_empresa, page, limit, search=search)


@router.get("/{combo_id}", response_model=ComboDTO)
def obter_combo(
    combo_id: int = Path(...),
    db: Session = Depends(get_db),
):
    svc = CombosService(db)
    return svc.obter(combo_id)


@router.post("/", response_model=ComboDTO, status_code=status.HTTP_201_CREATED)
async def criar_combo(
    empresa_id: int = Form(...),
    titulo: str = Form(...),
    descricao: str = Form(...),
    preco_total: float = Form(...),
    ativo: bool = Form(True),
    itens: str = Form(..., description="JSON de itens: [{produto_cod_barras, quantidade}]"),
    imagem: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    svc = CombosService(db)
    try:
        itens_list = json.loads(itens)
        req = CriarComboRequest(
            empresa_id=empresa_id,
            titulo=titulo,
            descricao=descricao,
            preco_total=preco_total,
            ativo=ativo,
            itens=itens_list,
        )
        return svc.criar(req, imagem=imagem)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{combo_id}", response_model=ComboDTO)
async def atualizar_combo(
    combo_id: int,
    titulo: str | None = Form(None),
    descricao: str | None = Form(None),
    preco_total: float | None = Form(None),
    ativo: bool | None = Form(None),
    itens: str | None = Form(None),  # JSON opcional
    imagem: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    svc = CombosService(db)
    try:
        req = AtualizarComboRequest(
            titulo=titulo,
            descricao=descricao,
            preco_total=preco_total,
            ativo=ativo,
            itens=(json.loads(itens) if itens is not None else None),
        )
        return svc.atualizar(combo_id, req, imagem=imagem)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{combo_id}/imagem", response_model=ComboDTO, status_code=status.HTTP_200_OK)
async def atualizar_imagem_combo(
    combo_id: int = Path(..., description="ID do combo"),
    cod_empresa: int = Form(..., description="ID da empresa dona do combo"),
    imagem: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Faz upload/atualização da imagem do combo no MinIO e salva a URL pública no campo `imagem`.

    - Envia como `multipart/form-data`
    - Campos: `cod_empresa` e `imagem`
    """
    if imagem.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Formato de imagem inválido")

    svc = CombosService(db)
    combo_dto = svc.obter(combo_id)
    if not combo_dto:
        raise HTTPException(status_code=404, detail="Combo não encontrado.")

    if int(combo_dto.empresa_id) != int(cod_empresa):
        raise HTTPException(status_code=400, detail="cod_empresa não confere com a empresa do combo.")

    try:
        nova_url = update_file_to_minio(
            db=db,
            cod_empresa=cod_empresa,
            file=imagem,
            slug="combos",
            url_antiga=combo_dto.imagem,
        )
    except Exception as e:
        logger.error(f"[Combos] Erro upload imagem - id={combo_id} empresa={cod_empresa}: {e}")
        raise HTTPException(status_code=500, detail="Erro ao fazer upload da imagem")

    # Atualiza apenas a imagem do combo usando o repositório diretamente
    combo_model = svc.repo.get_by_id(combo_id)
    combo_model = svc.repo.atualizar_combo(
        combo_model,
        titulo=None,
        descricao=None,
        preco_total=None,
        custo_total=None,
        ativo=None,
        imagem_url=nova_url,
        itens=None,
    )
    db.commit()
    db.refresh(combo_model)
    return svc._to_dto(combo_model)


@router.delete("/{combo_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_combo(
    combo_id: int,
    db: Session = Depends(get_db),
):
    svc = CombosService(db)
    svc.deletar(combo_id)
    return None

