from fastapi import APIRouter, Depends, Form, UploadFile, File, status
from sqlalchemy.orm import Session

from app.api.cadastros.schemas.schema_parceiros import (
    ParceiroIn, ParceiroOut, BannerParceiroIn, BannerParceiroOut
)
from app.api.cadastros.services.service_parceiros import ParceirosService
from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.minio_client import upload_file_to_minio

router = APIRouter(prefix="/api/cadastros/admin/parceiros", tags=["Admin - Cadastros - Parceiros"], dependencies=[Depends(get_current_user)])

# ======================================================================
# =========================== ENDPOINTS ADMIN ==========================
# ======================================================================

# CRUD Parceiros
@router.get("/", response_model=list[ParceiroOut])
def list_parceiros(db: Session = Depends(get_db)):
    """
    Lista parceiros cadastrados (endpoint admin)
    """
    return ParceirosService(db).list_parceiros()


@router.get("/{parceiro_id}", response_model=ParceiroOut)
def get_parceiro(parceiro_id: int, db: Session = Depends(get_db)):
    """
    Retorna dados de um parceiro específico (endpoint admin)
    """
    return ParceirosService(db).get_parceiro(parceiro_id)


@router.post("/", response_model=ParceiroOut, status_code=status.HTTP_201_CREATED)
def create_parceiro(body: ParceiroIn, db: Session = Depends(get_db)):
    """
    Cria um novo parceiro (endpoint admin)
    """
    return ParceirosService(db).create_parceiro(body)

@router.put("/{parceiro_id}", response_model=ParceiroOut)
def update_parceiro(parceiro_id: int, body: ParceiroIn, db: Session = Depends(get_db)):
    """
    Atualiza um parceiro existente (endpoint admin)
    """
    return ParceirosService(db).update_parceiro(parceiro_id, body.model_dump(exclude_unset=True))

@router.delete("/{parceiro_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_parceiro(parceiro_id: int, db: Session = Depends(get_db)):
    """
    Deleta um parceiro (endpoint admin)
    """
    return ParceirosService(db).delete_parceiro(parceiro_id)

# CRUD Banners
@router.post("/banners", response_model=BannerParceiroOut, status_code=status.HTTP_201_CREATED)
def create_banner(
    nome: str = Form(...),
    tipo_banner: str = Form(...),
    ativo: bool = Form(...),
    parceiro_id: int = Form(...),
    categoria_id: int | None = Form(None),
    link_redirecionamento: str | None = Form(None),
    landingpage_store: bool = Form(...),
    imagem: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    """
    Cria um novo banner para parceiro (endpoint admin)
    """
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
        link_redirecionamento=link_redirecionamento,
        landingpage_store=landingpage_store,
        imagem=imagem_url
    )
    return ParceirosService(db).create_banner(body)

@router.put("/banners/{banner_id}", response_model=BannerParceiroOut)
def update_banner(banner_id: int, body: BannerParceiroIn, db: Session = Depends(get_db)):
    """
    Atualiza um banner existente (endpoint admin)
    """
    return ParceirosService(db).update_banner(banner_id, body.model_dump(exclude_unset=True))

@router.delete("/banners/{banner_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_banner(banner_id: int, db: Session = Depends(get_db)):
    """
    Deleta um banner (endpoint admin)
    """
    return ParceirosService(db).delete_banner(banner_id)
