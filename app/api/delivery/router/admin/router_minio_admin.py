from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.minio_client import corrigir_permissoes_todos_buckets

router = APIRouter(prefix="/api/delivery/admin/minio", tags=["Admin - MinIO"], dependencies=[Depends(get_current_user)])

@router.post("/corrigir-permissoes")
def corrigir_permissoes_buckets(db: Session = Depends(get_db)):
    """
    Corrige permissões de todos os buckets do MinIO para permitir acesso público às imagens.
    Útil para resolver erros de "Access Denied" ao acessar imagens.
    """
    resultado = corrigir_permissoes_todos_buckets()
    return resultado
