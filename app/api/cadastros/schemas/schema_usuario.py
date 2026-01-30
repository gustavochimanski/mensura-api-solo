# app/api/mensura/schemas/schema_usuario.py
from typing import Optional, List, Any

from pydantic import BaseModel, ConfigDict, Field, AliasChoices, field_validator

class UserBase(BaseModel):
    username: str
    type_user: str
    # Compatibilidade:
    # - Frontend pode enviar `empresa_id` (int) ou `empresa_ids` (list[int]).
    empresa_ids: Optional[List[int]] = Field(
        default=None,
        validation_alias=AliasChoices("empresa_ids", "empresa_id"),
    )

    @field_validator("empresa_ids", mode="before")
    @classmethod
    def _coerce_empresa_ids(cls, v: Any):
        if v is None or v == "":
            return None
        # aceita empresa_id=1 (int) ou "1"
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            s = v.strip()
            if s.isdigit():
                return [int(s)]
        return v

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    type_user: Optional[str] = None
    empresa_ids: Optional[List[int]] = Field(
        default=None,
        validation_alias=AliasChoices("empresa_ids", "empresa_id"),
    )
    password: Optional[str] = None  # <- necessário para atualizar senha

    @field_validator("empresa_ids", mode="before")
    @classmethod
    def _coerce_empresa_ids(cls, v: Any):
        if v is None or v == "":
            return None
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            s = v.strip()
            if s.isdigit():
                return [int(s)]
        return v

class UserResponse(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
