# app/api/delivery/routes/parceiros_routes.py
from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.delivery.services.service_parceiros import ParceirosService
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.api.delivery.schemas.schema_parceiros import (
    ParceiroIn, ParceiroOut,
    BannerParceiroIn, BannerParceiroOut
)
from app.core.admin_dependencies import get_current_user
from app.utils.minio_client import upload_file_to_minio

router = APIRouter(prefix="/api/delivery", tags=["Delivery - Parceiros"])

# ===============================================================
# ====================== PARCEIROS ==============================
# ===============================================================
@router.post("/parceiros", response_model=ParceiroOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_user)])
def create_parceiro(body: ParceiroIn, db: Session = Depends(get_db)):
    return ParceirosService(db).create_parceiro(body)

@router.get("/parceiros", response_model=list[ParceiroOut])
def list_parceiros(db: Session = Depends(get_db)):
    return ParceirosService(db).list_parceiros()

@router.put("/parceiros/{parceiro_id}", response_model=ParceiroOut, dependencies=[Depends(get_current_user)])
def update_parceiro(parceiro_id: int, body: ParceiroIn, db: Session = Depends(get_db)):
    return ParceirosService(db).update_parceiro(parceiro_id, body.model_dump(exclude_unset=True))

@router.delete("/parceiros/{parceiro_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_user)])
def delete_parceiro(parceiro_id: int, db: Session = Depends(get_db)):
    return ParceirosService(db).delete_parceiro(parceiro_id)

# ===============================================================
# ====================== BANNERS ================================
# ===============================================================
from fastapi import Form, UploadFile, File

@router.post("/banners", response_model=BannerParceiroOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_user)])
def create_banner(
    nome: str = Form(...),
    tipo_banner: str = Form(...),
    ativo: bool = Form(...),
    parceiro_id: int = Form(...),
    imagem: UploadFile | None = File(None),
    db: Session = Depends(get_db)

):
    # 1️⃣ Se tiver arquivo, envia para o MinIO
    imagem_url = None
    if imagem:
        # slug usado no MinIO (pode ser "banners")
        slug = "banners"
        imagem_url = upload_file_to_minio(db, parceiro_id, imagem, "banners")

    # 2️⃣ Monta DTO
    body = BannerParceiroIn(
        nome=nome,
        tipo_banner=tipo_banner,
        ativo=ativo,
        parceiro_id=parceiro_id,
        imagem=imagem_url
    )

    # 3️⃣ Cria banner
    return ParceirosService(db).create_banner(body)

@router.get("/banners", response_model=list[BannerParceiroOut], dependencies=[Depends(get_current_user)])
def list_banners(parceiro_id: Optional[int] = None, db: Session = Depends(get_db)):
    return ParceirosService(db).list_banners(parceiro_id)

@router.put("/banners/{banner_id}", response_model=BannerParceiroOut, dependencies=[Depends(get_current_user)])
def update_banner(banner_id: int, body: BannerParceiroIn, db: Session = Depends(get_db)):
    return ParceirosService(db).update_banner(banner_id, body.model_dump(exclude_unset=True))

@router.delete("/banners/{banner_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_user)])
def delete_banner(banner_id: int, db: Session = Depends(get_db)):
    return ParceirosService(db).delete_banner(banner_id)



# ===============================================================
# ======================== CLIENT ===============================
# ===============================================================
@router.get("/client/banners", response_model=list[BannerParceiroOut])
def list_banners(parceiro_id: Optional[int] = None, db: Session = Depends(get_db)):
    return ParceirosService(db).list_banners(parceiro_id)
