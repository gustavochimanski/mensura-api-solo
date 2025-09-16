from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from typing import List

from app.api.delivery.models.model_cliente_dv import ClienteDeliveryModel
from app.api.delivery.schemas.schema_endereco import EnderecoCreate, EnderecoUpdate
from app.api.delivery.models.model_endereco_dv import EnderecoDeliveryModel

class EnderecoRepository:
    def __init__(self, db: Session):
        self.db = db

    # Listar todos endereços de um cliente
    def list_by_cliente(self, cliente_id: int):
        return (
            self.db.query(EnderecoDeliveryModel)
            .filter(EnderecoDeliveryModel.cliente_id == cliente_id)
            .order_by(EnderecoDeliveryModel.created_at.desc())
            .all()
        )

    # Buscar endereço específico
    def get_by_cliente(self, cliente_id: int, end_id: int):
        obj = (
            self.db.query(EnderecoDeliveryModel)
            .filter(
                EnderecoDeliveryModel.id == end_id,
                EnderecoDeliveryModel.cliente_id == cliente_id
            )
            .first()
        )
        if not obj:
            raise HTTPException(status_code=404, detail="Endereço não encontrado")
        return obj

    # Criar endereço
    def create(self, cliente_id: int, payload: EnderecoCreate):
        obj = EnderecoDeliveryModel(**payload.model_dump(), cliente_id=cliente_id)
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
        self.db.query(EnderecoDeliveryModel).filter(
            EnderecoDeliveryModel.cliente_id == cliente_id
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
            self.db.query(EnderecoDeliveryModel)
            .filter(
                EnderecoDeliveryModel.cliente_id == cliente_id,
                EnderecoDeliveryModel.logradouro == payload.logradouro,
                EnderecoDeliveryModel.numero == payload.numero,
                EnderecoDeliveryModel.bairro == payload.bairro,
                EnderecoDeliveryModel.cidade == payload.cidade,
                EnderecoDeliveryModel.estado == payload.estado,
                EnderecoDeliveryModel.cep == payload.cep
            )
        )
        
        # Se exclude_id foi fornecido, exclui esse ID da verificação
        if exclude_id is not None:
            query = query.filter(EnderecoDeliveryModel.id != exclude_id)
        
        endereco_existente = query.first()
        return endereco_existente is not None