from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.api.mensura.repositories.usuarios_repo import UsuarioRepository
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.mensura.schemas.usuario_schema import UserCreate, UserUpdate
from app.api.mensura.models.user_model import UserModel

class UserService:
    def __init__(self, db: Session):
        self.repo = UsuarioRepository(db)
        self.repo_emp = EmpresaRepository(db)

    def get_user(self, id: int):
        user = self.repo.get(id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        return user

    def list_users(self, skip: int = 0, limit: int = 100):
        return self.repo.list(skip, limit)

    def create_user(self, data: UserCreate):
        # 🔒 Verifica se já existe usuário com mesmo CPF
        if self.repo.get_by_cpf(data.cpf):
            raise HTTPException(status_code=400, detail="Já existe um usuário com este CPF")

        # 🔒 Verifica se já existe usuário com mesmo username
        if self.repo.get_by_username(data.username):
            raise HTTPException(status_code=400, detail="Já existe um usuário com este username")

        # 🔎 (Opcional) Validação de tipo_user
        if data.type_user not in ['admin', 'cliente', 'funcionario']:
            raise HTTPException(status_code=400, detail="Tipo de usuário inválido")

        # 🔗 Valida se as empresas informadas existem
        empresas = []
        if data.empresa_ids:
            empresas = self.repo_emp.get_by_ids(data.empresa_ids)
            if len(empresas) != len(set(data.empresa_ids)):
                raise HTTPException(status_code=400, detail="Uma ou mais empresas não foram encontradas")

        # ✅ Criação do modelo
        user = UserModel(
            username=data.username,
            hashed_password=data.password,  # Obs: ideal fazer hash antes
            type_user=data.type_user,
            cpf=data.cpf,
            empresas=empresas  # se tiver relacionamento many-to-many
        )

        return self.repo.create(user)

    def update_user(self, id: int, data: UserUpdate):
        user = self.get_user(id)

        # 🔒 Evita duplicação de CPF se for alterar
        if data.cpf and data.cpf != user.cpf:
            if self.repo.get_by_cpf(data.cpf):
                raise HTTPException(status_code=400, detail="Já existe um usuário com este CPF")

        # 🔒 Evita duplicação de username se for alterar
        if data.username and data.username != user.username:
            if self.repo.get_by_username(data.username):
                raise HTTPException(status_code=400, detail="Já existe um usuário com este username")

        return self.repo.update(user, data.dict(exclude_unset=True))

    def delete_user(self, id: int):
        user = self.get_user(id)
        self.repo.delete(user)
