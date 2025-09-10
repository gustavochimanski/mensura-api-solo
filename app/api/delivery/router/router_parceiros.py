from fastapi import APIRouter, Depends, Form, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.delivery.schemas.schema_parceiros import (
    ParceiroIn, ParceiroOut, BannerParceiroIn, BannerParceiroOut, ParceiroCompletoOut
)
from app.api.delivery.schemas.schema_cupom import CupomLinkOut, CupomParceiroOut
from app.api.delivery.services.service_parceiros import ParceirosService
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.database.db_connection import get_db
from app.core.admin_dependencies import get_current_user
from app.utils.minio_client import upload_file_to_minio

router = APIRouter(prefix="/api/delivery", tags=["Delivery - Parceiros"])

# CRUD Parceiros
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

# CRUD Banners
@router.post("/banners", response_model=BannerParceiroOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends()])
def create_banner(
    nome: str = Form(...),
    tipo_banner: str = Form(...),
    ativo: bool = Form(...),
    parceiro_id: int = Form(...),
    categoria_id: int = Form(...),
    imagem: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):

    empresa = EmpresaRepository(db).get_first()
    imagem_url = None
    if imagem:
        imagem_url = upload_file_to_minio(db, empresa.id, imagem, "banners")

    body = BannerParceiroIn(
        nome=nome,
        tipo_banner=tipo_banner,
        ativo=ativo,
        parceiro_id=parceiro_id,
        categoria_id=categoria_id,
        imagem=imagem_url
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

# Parceiro completo (banners + cupons + links)
@router.get("/parceiros/{parceiro_id}/full", response_model=ParceiroCompletoOut)
def get_parceiro_completo(parceiro_id: int, db: Session = Depends(get_db)):
    parceiro = ParceirosService(db).get_parceiro_completo(parceiro_id)
    return ParceiroCompletoOut(
        id=parceiro.id,
        nome=parceiro.nome,
        ativo=parceiro.ativo,
        telefone=parceiro.telefone,
        cupons=[
            CupomParceiroOut(
                id=c.id,
                codigo=c.codigo,
                descricao=c.descricao,
                desconto_valor=float(c.desconto_valor) if c.desconto_valor is not None else None,
                desconto_percentual=float(c.desconto_percentual) if c.desconto_percentual is not None else None,
                ativo=c.ativo,
                monetizado=c.monetizado,
                valor_por_lead=float(c.valor_por_lead) if c.valor_por_lead is not None else None,
                links=[CupomLinkOut.from_orm(l) for l in c.links]
            ) for c in parceiro.cupons
        ],
        banners=[
            BannerParceiroOut(
                id=b.id,
                nome=b.nome,
                ativo=b.ativo,
                tipo_banner=b.tipo_banner,
                imagem=b.imagem,
                categoria_id=b.categoria_id,
                href_destino=b.href_destino
            ) for b in parceiro.banners
        ]
    )
