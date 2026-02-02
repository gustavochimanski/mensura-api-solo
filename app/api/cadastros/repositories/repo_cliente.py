from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.utils.telefone import variantes_telefone_para_busca

class ClienteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_token(self, token: str) -> Optional[ClienteModel]:
        return self.db.query(ClienteModel).filter_by(super_token=token).first()

    def get_by_telefone(self, telefone: str) -> Optional[ClienteModel]:
        candidatos = variantes_telefone_para_busca(telefone)
        if not candidatos:
            return None
        # 1 query só (inclui com/sem 55 e com/sem 9 quando aplicável)
        return (
            self.db.query(ClienteModel)
            .filter(ClienteModel.telefone.in_(candidatos))
            .first()
        )

    def get_by_email(self, email: str) -> Optional[ClienteModel]:
        return self.db.query(ClienteModel).filter_by(email=email).first()

    def get_by_cpf(self, cpf: str) -> Optional[ClienteModel]:
        return self.db.query(ClienteModel).filter_by(cpf=cpf).first()

    def get_by_id(self, id: int) -> Optional[ClienteModel]:
        return self.db.query(ClienteModel).filter(ClienteModel.id == id).first()

    def list(
        self,
        ativo: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ClienteModel]:
        stmt = select(ClienteModel)
        if ativo is not None:
            stmt = stmt.where(ClienteModel.ativo.is_(ativo))

        if search is not None:
            s = search.strip()
            if s:
                like = f"%{s}%"
                conditions = [
                    ClienteModel.nome.ilike(like),
                    ClienteModel.email.ilike(like),
                    ClienteModel.cpf.ilike(like),
                    ClienteModel.telefone.ilike(like),
                ]

                # Se o usuário digitar telefone (com/sem 55, com/sem 9),
                # tentamos bater também via conjunto de variantes.
                candidatos = variantes_telefone_para_busca(s)
                if candidatos:
                    conditions.append(ClienteModel.telefone.in_(candidatos))

                stmt = stmt.where(or_(*conditions))

        # Ordenação estável e paginação
        stmt = stmt.order_by(ClienteModel.id.desc()).offset(int(skip)).limit(int(limit))
        return self.db.execute(stmt).scalars().all()

    def create(self, **data) -> ClienteModel:
        obj = ClienteModel(**data)
        self.db.add(obj)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise
        self.db.refresh(obj)
        return obj

    def update(self, db_obj: ClienteModel, **data) -> ClienteModel:
        for k, v in data.items():
            # Garante que CPF vazio seja convertido para None para evitar violação de constraint única
            if k == 'cpf' and isinstance(v, str) and v.strip() == "":
                v = None
            setattr(db_obj, k, v)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise
        self.db.refresh(db_obj)
        return db_obj

    def set_ativo(self, token: str, ativo: bool) -> Optional[ClienteModel]:
        obj = self.get_by_token(token)
        if not obj:
            return None
        obj.ativo = ativo
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get_enderecos(self, cliente_id: int) -> List:
        """Busca todos os endereços de um cliente específico por ID"""
        from app.api.cadastros.models.model_endereco_dv import EnderecoModel
        return (
            self.db.query(EnderecoModel)
            .filter(EnderecoModel.cliente_id == cliente_id)
            .order_by(EnderecoModel.created_at.desc())
            .all()
        )
