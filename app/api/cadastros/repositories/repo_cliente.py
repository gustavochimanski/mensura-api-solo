from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.utils.telefone import normalizar_telefone, variantes_celular_para_busca

class ClienteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_token(self, token: str) -> Optional[ClienteModel]:
        return self.db.query(ClienteModel).filter_by(super_token=token).first()

    def get_by_telefone(self, telefone: str) -> Optional[ClienteModel]:
        telefone_norm = normalizar_telefone(telefone)
        if not telefone_norm:
            return None

        # Lista de candidatos: número exato + variantes com/sem o "9" de celular
        candidatos = variantes_celular_para_busca(telefone_norm)
        for tel in candidatos:
            cliente = self.db.query(ClienteModel).filter_by(telefone=tel).first()
            if cliente:
                return cliente
            # Compatibilidade: bases antigas podem ter salvo sem o prefixo 55
            if tel.startswith("55") and len(tel) > 2:
                cliente = self.db.query(ClienteModel).filter_by(telefone=tel[2:]).first()
                if cliente:
                    return cliente

        return None

    def get_by_email(self, email: str) -> Optional[ClienteModel]:
        return self.db.query(ClienteModel).filter_by(email=email).first()

    def get_by_cpf(self, cpf: str) -> Optional[ClienteModel]:
        return self.db.query(ClienteModel).filter_by(cpf=cpf).first()

    def get_by_id(self, id: int) -> Optional[ClienteModel]:
        return self.db.query(ClienteModel).filter(ClienteModel.id == id).first()

    def list(self, ativo: Optional[bool] = None) -> List[ClienteModel]:
        stmt = select(ClienteModel)
        if ativo is not None:
            stmt = stmt.where(ClienteModel.ativo.is_(ativo))
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
