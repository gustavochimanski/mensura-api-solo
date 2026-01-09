# app/api/mensura/schemas/schema_usuario.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class UserBase(BaseModel):
    username: str
    type_user: str
    empresa_ids: Optional[List[int]] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    type_user: Optional[str] = None
    empresa_ids: Optional[List[int]] = None
    password: Optional[str] = None  # <- necessário para atualizar senha

class UserResponse(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
