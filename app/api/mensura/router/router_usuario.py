# app/api/mensura/router/router_usuario.py
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.mensura.services.usuario_service import UserService
from app.api.mensura.schemas.usuario_schema import UserCreate, UserUpdate, UserResponse

router = APIRouter(prefix="/api/mensura/usuarios", tags=["Usuarios"])

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
