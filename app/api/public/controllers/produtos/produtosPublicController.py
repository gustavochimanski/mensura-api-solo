from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from app.api.public.repositories.CadProdPublic_repo import CadProdPublicRepository
from app.database.db_connection import get_db

router = APIRouter()

@router.get("api/public/produtos")
def get_paginated_products(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100)
):
    repo = CadProdPublicRepository(db)
    return repo.get_paginated(page=page, limit=limit)



@router.put("api/public/produtos/{produto_id}")
def put_product_by_fied(
    produto_id: int,
    field: str = Query(..., description="Nome do campo a ser atualizado"),
    value: str = Body(..., embed=True, description="Novo valor para o campo"),
    db: Session = Depends(get_db),
):
    repo = CadProdPublicRepository(db)
    return repo.put_by_filed(produto_id, field, value)