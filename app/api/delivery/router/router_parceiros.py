# app/api/delivery/routes/parceiros_routes.py
from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.delivery.services.service_parceiros import ParceirosService
from app.database.db_connection import get_db
from app.api.delivery.schemas.schema_parceiros import (
    ParceiroIn, ParceiroOut,
    BannerParceiroIn, BannerParceiroOut
)
from app.core.admin_dependencies import get_current_user

router = APIRouter(prefix="/api/delivery/parceiros", tags=["Delivery - Parceiros"])

# -------- PARCEIROS --------
@router.post("", response_model=ParceiroOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_user)])
def create_parceiro(body: ParceiroIn, db: Session = Depends(get_db)):
    return ParceirosService(db).create_parceiro(body)

@router.get("", response_model=list[ParceiroOut])
def list_parceiros(db: Session = Depends(get_db)):
    return ParceirosService(db).list_parceiros()

@router.put("/{parceiro_id}", response_model=ParceiroOut, dependencies=[Depends(get_current_user)])
def update_parceiro(parceiro_id: int, body: ParceiroIn, db: Session = Depends(get_db)):
    return ParceirosService(db).update_parceiro(parceiro_id, body.model_dump(exclude_unset=True))

@router.delete("/{parceiro_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_user)])
def delete_parceiro(parceiro_id: int, db: Session = Depends(get_db)):
    return ParceirosService(db).delete_parceiro(parceiro_id)

# -------- BANNERS --------
from fastapi import Form, UploadFile, File

@router.post("/banners", response_model=BannerParceiroOut, status_code=status.HTTP_201_CREATED)
def create_banner(
    nome: str = Form(...),
    tipo_banner: str = Form(...),
    ativo: bool = Form(...),
    parceiro_id: int = Form(...),
    imagem: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    body = BannerParceiroIn(
        nome=nome,
        tipo_banner=tipo_banner,
        ativo=ativo,
        parceiro_id=parceiro_id,
        imagem=imagem.filename if imagem else None
    )
    return ParceirosService(db).create_banner(body)


@router.get("/banners", response_model=list[BannerParceiroOut])
def list_banners(parceiro_id: Optional[int] = None, db: Session = Depends(get_db)):
    return ParceirosService(db).list_banners(parceiro_id)

@router.put("/banners/{banner_id}", response_model=BannerParceiroOut, dependencies=[Depends(get_current_user)])
def update_banner(banner_id: int, body: BannerParceiroIn, db: Session = Depends(get_db)):
    return ParceirosService(db).update_banner(banner_id, body.model_dump(exclude_unset=True))

@router.delete("/banners/{banner_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_user)])
def delete_banner(banner_id: int, db: Session = Depends(get_db)):
    return ParceirosService(db).delete_banner(banner_id)
