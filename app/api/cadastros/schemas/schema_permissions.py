from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PermissionResponse(BaseModel):
    id: int
    key: str
    domain: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserPermissionKeysResponse(BaseModel):
    user_id: int
    empresa_id: int
    permission_keys: List[str]


class SetUserPermissionsRequest(BaseModel):
    permission_keys: List[str] = Field(
        default_factory=list,
        description="Lista de keys. Formato suportado: route:/... (ex: route:/pedidos, route:/configuracoes:usuarios).",
    )

