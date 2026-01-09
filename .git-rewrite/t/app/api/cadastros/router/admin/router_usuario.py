# app/api/mensura/router/router_usuario.py
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.cadastros.services.usuario_service import UserService
from app.api.cadastros.schemas.schema_usuario import UserCreate, UserUpdate, UserResponse
from app.core.admin_dependencies import get_current_user

router = APIRouter(prefix="/api/mensura/admin/usuarios", tags=["Admin - Mensura - Usuarios"], dependencies=[Depends(get_current_user)])

@router.post("/", response_model=UserResponse)
def create_user(request: UserCreate, db: Session = Depends(get_db)):
    return UserService(db).create_user(request)

@router.get("/{id}", response_model=UserResponse)
def get_user(id: int, db: Session = Depends(get_db)):
    return UserService(db).get_user(id)

@router.get("/", response_model=List[UserResponse])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return UserService(db).list_users(skip, limit)

@router.put("/{id}", response_model=UserResponse)
def update_user(id: int, request: UserUpdate, db: Session = Depends(get_db)):
    return UserService(db).update_user(id, request)

@router.delete("/{id}", status_code=204)
def delete_user(id: int, db: Session = Depends(get_db)):
    UserService(db).delete_user(id)
