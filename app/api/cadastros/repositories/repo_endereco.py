from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from typing import List

from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.api.cardapio.schemas.schema_endereco import EnderecoCreate, EnderecoUpdate
from app.api.cadastros.models.model_endereco_dv import EnderecoModel

class EnderecoRepository:
    def __init__(self, db: Session):
        self.db = db

    # Listar todos endereços de um cliente
    def list_by_cliente(self, cliente_id: int):
        return (
            self.db.query(EnderecoModel)
            .filter(EnderecoModel.cliente_id == cliente_id)
            .order_by(EnderecoModel.created_at.desc())
            .all()
        )

    # Buscar endereço específico
    def get_by_cliente(self, cliente_id: int, end_id: int):
        obj = (
            self.db.query(EnderecoModel)
            .filter(
                EnderecoModel.id == end_id,
                EnderecoModel.cliente_id == cliente_id
            )
            .first()
        )
        if not obj:
            raise HTTPException(status_code=404, detail="Endereço não encontrado")
        return obj

    # Criar endereço
    def create(self, cliente_id: int, payload: EnderecoCreate):
        dados_endereco = payload.model_dump(exclude={"cliente_id"})
        obj = EnderecoModel(**dados_endereco, cliente_id=cliente_id)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    # Atualizar endereço
    def update(self, cliente_id: int, end_id: int, payload: EnderecoUpdate):
        obj = self.get_by_cliente(cliente_id, end_id)
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    # Deletar endereço
    def delete(self, cliente_id: int, end_id: int):
        obj = self.get_by_cliente(cliente_id, end_id)
        self.db.delete(obj)
        self.db.commit()

    # Marcar endereço como principal
    def set_padrao(self, cliente_id: int, end_id: int):
        # Zera padrão dos outros endereços
        self.db.query(EnderecoModel).filter(
            EnderecoModel.cliente_id == cliente_id
        ).update({"is_principal": False})
        obj = self.get_by_cliente(cliente_id, end_id)
        obj.is_principal = True
        self.db.commit()
        self.db.refresh(obj)
        return obj

    # Verificar se endereço já existe
    def endereco_existe(self, cliente_id: int, payload: EnderecoCreate, exclude_id: int = None) -> bool:
        """
        Verifica se um endereço já existe para um cliente específico.
        Compara logradouro, número, bairro, cidade, UF e CEP.
        Se exclude_id for fornecido, exclui esse ID da verificação (útil para updates).
        """
        query = (
            self.db.query(EnderecoModel)
            .filter(
                EnderecoModel.cliente_id == cliente_id,
                EnderecoModel.logradouro == payload.logradouro,
                EnderecoModel.numero == payload.numero,
                EnderecoModel.bairro == payload.bairro,
                EnderecoModel.cidade == payload.cidade,
                EnderecoModel.estado == payload.estado,
                EnderecoModel.cep == payload.cep
            )
        )
        
        # Se exclude_id foi fornecido, exclui esse ID da verificação
        if exclude_id is not None:
            query = query.filter(EnderecoModel.id != exclude_id)
        
        endereco_existente = query.first()
        return endereco_existente is not None

