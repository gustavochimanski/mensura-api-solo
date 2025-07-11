# app/mensura/schemas/auth_schema.py
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    token_type: str = "bearer"
    type_user: str = "user"
    access_token: str
