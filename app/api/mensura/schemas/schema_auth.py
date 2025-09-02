# app/api/mensura/schemas/schema_auth.py
from pydantic import BaseModel, ConfigDict

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    token_type: str = "bearer"
    type_user: str = "user"
    access_token: str
    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    id: int
    username: str
    type_user: str
    model_config = ConfigDict(from_attributes=True)
