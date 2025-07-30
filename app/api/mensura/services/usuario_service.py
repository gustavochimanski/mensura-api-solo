# app/api/mensura/services/usuario_service.py
from fastapi import HTTPException
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from app.api.mensura.repositories.usuarios_repo import UsuarioRepository
from app.api.mensura.repositories.empresa_repo  import EmpresaRepository
from app.api.mensura.schemas.usuario_schema import UserCreate, UserUpdate
from app.api.mensura.models.user_model      import UserModel

class UserService:
    def __init__(self, db: Session):
        self.repo     = UsuarioRepository(db)
        self.repo_emp = EmpresaRepository(db)

    def get_user(self, id: int):
        user = self.repo.get(id)
        if not user:
            raise HTTPException(404, "Usuário não encontrado")
        return user

    def list_users(self, skip: int = 0, limit: int = 100):
        return self.repo.list(skip, limit)

    def create_user(self, data: UserCreate):
        # 🔒 Verifica username único
        if self.repo.get_by_username(data.username):
            raise HTTPException(400, "Já existe um usuário com este username")

        # 🔎 Validação de type_user
        if data.type_user not in ["admin", "cliente", "funcionario"]:
            raise HTTPException(400, "Tipo de usuário inválido")

        # 🔗 Carrega e valida empresas
        empresas = []
        if data.empresa_ids:
            empresas = self.repo_emp.list_by_ids(data.empresa_ids)
            if len(empresas) != len(set(data.empresa_ids)):
                raise HTTPException(400, "Uma ou mais empresas não foram encontradas")

        # ✅ Cria o UserModel (já com hash de senha)
        user = UserModel(
            username=data.username,
            hashed_password=bcrypt.hash(data.password),
            type_user=data.type_user,
            empresas=empresas
        )
        return self.repo.create(user)

    def update_user(self, id: int, data: UserUpdate):
        user = self.get_user(id)

        # 🔒 Evita duplicar username
        if data.username and data.username != user.username:
            if self.repo.get_by_username(data.username):
                raise HTTPException(400, "Já existe um usuário com este username")

        # Atualiza campos básicos
        update_data = data.dict(exclude_unset=True, exclude={"empresa_ids"})
        if "password" in data.__fields_set__:
            update_data["hashed_password"] = bcrypt.hash(data.password)

        # 🔗 Atualiza relação many-to-many
        if data.empresa_ids is not None:
            empresas = self.repo_emp.list_by_ids(data.empresa_ids)
            if len(empresas) != len(set(data.empresa_ids)):
                raise HTTPException(400, "Uma ou mais empresas não foram encontradas")
            user.empresas = empresas

        return self.repo.update(user, update_data)

    def delete_user(self, id: int):
        user = self.get_user(id)
        self.repo.delete(user)
