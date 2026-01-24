# app/api/mensura/services/usuario_service.py
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.cadastros.repositories.usuarios_repo import UsuarioRepository
from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.cadastros.schemas.schema_usuario import UserCreate, UserUpdate
from app.api.cadastros.models.user_model import UserModel
from app.api.caixas.models.model_caixa_abertura import CaixaAberturaModel
from app.api.caixas.models.model_retirada import RetiradaModel
from app.core.security import hash_password


class UserService:
    def __init__(self, db: Session):
        self.db = db
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
        # Aberturas de caixa usam ondelete=RESTRICT (usuario_id_abertura), então a remoção deve ser bloqueada
        # enquanto existirem registros vinculados.
        aberturas_qtd = (
            self.db.query(func.count(CaixaAberturaModel.id))
            .filter(CaixaAberturaModel.usuario_id_abertura == id)
            .scalar()
            or 0
        )
        retiradas_qtd = (
            self.db.query(func.count(RetiradaModel.id))
            .filter(RetiradaModel.usuario_id == id)
            .scalar()
            or 0
        )

        itens_bloqueio: list[str] = []
        if aberturas_qtd > 0:
            itens_bloqueio.append(f"{aberturas_qtd} abertura(s) de caixa")
        if retiradas_qtd > 0:
            itens_bloqueio.append(f"{retiradas_qtd} retirada(s) de caixa")

        if itens_bloqueio:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Não é possível remover o usuário porque ainda existem registros vinculados: "
                    + "; ".join(itens_bloqueio)
                    + "."
                ),
            )

        try:
            self.repo.delete(user)
        except IntegrityError as e:
            # Garante rollback para evitar sessão em estado inválido e retorna erro amigável.
            self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"Não é possível remover o usuário por restrição de integridade: {str(e.orig)}",
            )
