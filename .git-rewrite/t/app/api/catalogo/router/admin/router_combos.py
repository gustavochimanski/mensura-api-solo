from fastapi import APIRouter, Depends, Query, Path, HTTPException
from fastapi import status, UploadFile, Form
from sqlalchemy.orm import Session
import json

from app.api.catalogo.schemas.schema_combo import (
    CriarComboRequest,
    AtualizarComboRequest,
    ListaCombosResponse,
    ComboDTO,
)
from app.api.catalogo.services.service_combo import CombosService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db


router = APIRouter(prefix="/api/catalogo/admin/combos", tags=["Admin - Catalogo - Combos"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=ListaCombosResponse)
def listar_combos(
    cod_empresa: int = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    svc = CombosService(db)
    return svc.listar(cod_empresa, page, limit)


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


@router.delete("/{combo_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_combo(
    combo_id: int,
    db: Session = Depends(get_db),
):
    svc = CombosService(db)
    svc.deletar(combo_id)
    return None

