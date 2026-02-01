# app/api/mensura/services/usuario_service.py
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.cadastros.repositories.usuarios_repo import UsuarioRepository
from app.api.cadastros.models.association_tables import usuario_empresa
from app.api.cadastros.models.model_user_permission import UserPermissionModel
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

    def _is_super(self, actor: UserModel | None) -> bool:
        return bool(actor and getattr(actor, "type_user", None) == "super")

    def _assert_user_has_empresa_access(self, user_id: int, empresa_id: int) -> None:
        """
        Garante que o usuário tenha acesso/vínculo com a empresa informada.

        Regras (compatíveis com app.core.authorization):
        - vínculo explícito em `cadastros.usuario_empresa`, OU
        - existência de ao menos uma permissão em `cadastros.user_permissions`.
        """
        stmt = (
            select(usuario_empresa.c.empresa_id)
            .where(
                usuario_empresa.c.usuario_id == int(user_id),
                usuario_empresa.c.empresa_id == int(empresa_id),
            )
            .limit(1)
        )
        ok = self.db.execute(stmt).first()
        if ok:
            return

        has_perm = (
            self.db.query(UserPermissionModel.permission_id)
            .filter(
                UserPermissionModel.user_id == int(user_id),
                UserPermissionModel.empresa_id == int(empresa_id),
            )
            .first()
        )
        if has_perm:
            return

        raise HTTPException(status_code=403, detail="Você não tem acesso a esta empresa")

    def get_user(self, id: int, empresa_id_scope: int | None = None, actor: UserModel | None = None):
        user = self.repo.get(id)
        if not user:
            raise HTTPException(404, "Usuário não encontrado")
        if empresa_id_scope is not None and not self._is_super(actor):
            self._assert_user_has_empresa_access(user_id=id, empresa_id=int(empresa_id_scope))
        return user

    def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        empresa_id_scope: int | None = None,
        actor: UserModel | None = None,
    ):
        if empresa_id_scope is None or self._is_super(actor):
            return self.repo.list(skip, limit)

        # Escopo por empresa (tenant): lista apenas usuários vinculados à empresa.
        q = (
            self.db.query(UserModel)
            .join(usuario_empresa, usuario_empresa.c.usuario_id == UserModel.id)
            .filter(usuario_empresa.c.empresa_id == int(empresa_id_scope))
            .distinct()
            .offset(skip)
        )
        if limit:
            q = q.limit(limit)
        return q.all()

    def create_user(
        self,
        data: UserCreate,
        empresa_id_scope: int | None = None,
        actor: UserModel | None = None,
    ):
        if self.repo.get_by_username(data.username):
            raise HTTPException(400, "Já existe um usuário com este username")

        if data.type_user not in ["cliente", "funcionario"]:
            raise HTTPException(400, "Tipo de usuário inválido")

        empresas = []
        requested_empresa_ids = list(data.empresa_ids or [])

        if empresa_id_scope is not None and not self._is_super(actor):
            scope_id = int(empresa_id_scope)
            # Se não veio empresa no payload, assume a empresa do contexto.
            if not requested_empresa_ids:
                requested_empresa_ids = [scope_id]

            # Impede criar usuário "fora" do tenant atual.
            if scope_id not in requested_empresa_ids:
                raise HTTPException(
                    status_code=400,
                    detail="empresa_id do contexto deve estar incluído em empresa_ids",
                )

            # Impede vincular o novo usuário a empresas que o ator não acessa.
            if actor is not None:
                for eid in set(requested_empresa_ids):
                    self._assert_user_has_empresa_access(user_id=actor.id, empresa_id=int(eid))

        if requested_empresa_ids:
            empresas = self.repo_emp.list_by_ids(requested_empresa_ids)
            if len(empresas) != len(set(requested_empresa_ids)):
                raise HTTPException(400, "Uma ou mais empresas não foram encontradas")

        user = UserModel(
            username=data.username,
            hashed_password=hash_password(data.password),
            type_user=data.type_user,
            empresas=empresas,
        )
        return self.repo.create(user)

    def update_user(
        self,
        id: int,
        data: UserUpdate,
        empresa_id_scope: int | None = None,
        actor: UserModel | None = None,
    ):
        user = self.get_user(id, empresa_id_scope=empresa_id_scope, actor=actor)

        if data.username and data.username != user.username:
            if self.repo.get_by_username(data.username):
                raise HTTPException(400, "Já existe um usuário com este username")

        update_data = data.model_dump(exclude_unset=True, exclude={"empresa_ids", "password"})
        if data.password:
            update_data["hashed_password"] = hash_password(data.password)

        if data.type_user is not None and data.type_user not in ["cliente", "funcionario"]:
            raise HTTPException(400, "Tipo de usuário inválido")

        if data.empresa_ids is not None:
            requested_empresa_ids = list(data.empresa_ids or [])

            if empresa_id_scope is not None and not self._is_super(actor):
                scope_id = int(empresa_id_scope)
                if scope_id not in requested_empresa_ids:
                    raise HTTPException(
                        status_code=400,
                        detail="Não é permitido remover o vínculo do usuário com a empresa do contexto",
                    )
                if actor is not None:
                    for eid in set(requested_empresa_ids):
                        self._assert_user_has_empresa_access(user_id=actor.id, empresa_id=int(eid))

            empresas = self.repo_emp.list_by_ids(requested_empresa_ids)
            if len(empresas) != len(set(requested_empresa_ids)):
                raise HTTPException(400, "Uma ou mais empresas não foram encontradas")
            user.empresas = empresas

        return self.repo.update(user, update_data)

    def delete_user(self, id: int, empresa_id_scope: int | None = None, actor: UserModel | None = None):
        user = self.get_user(id, empresa_id_scope=empresa_id_scope, actor=actor)
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
            # Cleanup explícito de vínculos (para garantir remoção mesmo se o DB não estiver com CASCADE aplicado).
            # - Usuario ↔ Empresa (cadastros.usuario_empresa)
            # - Permissões por usuário/empresa (cadastros.user_permissions)
            self.db.query(UserPermissionModel).filter(UserPermissionModel.user_id == id).delete(
                synchronize_session=False
            )
            self.db.execute(usuario_empresa.delete().where(usuario_empresa.c.usuario_id == id))

            self.repo.delete(user)
        except IntegrityError as e:
            # Garante rollback para evitar sessão em estado inválido e retorna erro amigável.
            self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"Não é possível remover o usuário por restrição de integridade: {str(e.orig)}",
            )
