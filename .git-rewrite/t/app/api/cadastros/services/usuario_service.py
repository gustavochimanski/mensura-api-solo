# app/api/mensura/services/usuario_service.py
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.cadastros.repositories.usuarios_repo import UsuarioRepository
from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.cadastros.schemas.schema_usuario import UserCreate, UserUpdate
from app.api.cadastros.models.user_model import UserModel
from app.core.security import hash_password


class UserService:
    def __init__(self, db: Session):
        self.repo = UsuarioRepository(db)
        self.repo_emp = EmpresaRepository(db)

    def get_user(self, id: int):
        user = self.repo.get(id)
        if not user:
            raise HTTPException(404, "Usuário não encontrado")
        return user

    def list_users(self, skip: int = 0, limit: int = 100):
        return self.repo.list(skip, limit)

    def create_user(self, data: UserCreate):
        if self.repo.get_by_username(data.username):
            raise HTTPException(400, "Já existe um usuário com este username")

        if data.type_user not in ["admin", "cliente", "funcionario"]:
            raise HTTPException(400, "Tipo de usuário inválido")

        empresas = []
        if data.empresa_ids:
            empresas = self.repo_emp.list_by_ids(data.empresa_ids)
            if len(empresas) != len(set(data.empresa_ids)):
                raise HTTPException(400, "Uma ou mais empresas não foram encontradas")

        user = UserModel(
            username=data.username,
            hashed_password=hash_password(data.password),
            type_user=data.type_user,
            empresas=empresas,
        )
        return self.repo.create(user)

    def update_user(self, id: int, data: UserUpdate):
        user = self.get_user(id)

        if data.username and data.username != user.username:
            if self.repo.get_by_username(data.username):
                raise HTTPException(400, "Já existe um usuário com este username")

        update_data = data.model_dump(exclude_unset=True, exclude={"empresa_ids", "password"})
        if data.password:
            update_data["hashed_password"] = hash_password(data.password)

        if data.empresa_ids is not None:
            empresas = self.repo_emp.list_by_ids(data.empresa_ids)
            if len(empresas) != len(set(data.empresa_ids)):
                raise HTTPException(400, "Uma ou mais empresas não foram encontradas")
            user.empresas = empresas

        return self.repo.update(user, update_data)

    def delete_user(self, id: int):
        user = self.get_user(id)
        self.repo.delete(user)
