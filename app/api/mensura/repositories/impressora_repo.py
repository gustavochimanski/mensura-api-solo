# app/api/mensura/repositories/impressora_repo.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from app.api.mensura.models.impressora_model import ImpressoraModel
from app.api.mensura.schemas.schema_impressora import ImpressoraCreate, ImpressoraUpdate

class ImpressoraRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_impressora(self, impressora_data: ImpressoraCreate) -> ImpressoraModel:
        db_impressora = ImpressoraModel(
            nome=impressora_data.nome,
            nome_impressora=impressora_data.config.nome_impressora,
            fonte_nome=impressora_data.config.fonte_nome,
            fonte_tamanho=impressora_data.config.fonte_tamanho,
            espacamento_linha=impressora_data.config.espacamento_linha,
            espacamento_item=impressora_data.config.espacamento_item,
            nome_estabelecimento=impressora_data.config.nome_estabelecimento,
            mensagem_rodape=impressora_data.config.mensagem_rodape,
            formato_preco=impressora_data.config.formato_preco,
            formato_total=impressora_data.config.formato_total,
            empresa_id=impressora_data.empresa_id
        )
        self.db.add(db_impressora)
        self.db.commit()
        self.db.refresh(db_impressora)
        return db_impressora

    def get_impressora_by_id(self, impressora_id: int) -> Optional[ImpressoraModel]:
        return self.db.query(ImpressoraModel).filter(ImpressoraModel.id == impressora_id).first()

    def get_impressoras_by_empresa(self, empresa_id: int) -> List[ImpressoraModel]:
        return self.db.query(ImpressoraModel).filter(ImpressoraModel.empresa_id == empresa_id).all()

    def update_impressora(self, impressora_id: int, impressora_data: ImpressoraUpdate) -> Optional[ImpressoraModel]:
        db_impressora = self.get_impressora_by_id(impressora_id)
        if not db_impressora:
            return None

        update_data = impressora_data.model_dump(exclude_unset=True)
        
        # Atualizar campos básicos
        if "nome" in update_data:
            db_impressora.nome = update_data["nome"]
        
        # Atualizar campos de configuração
        if "config" in update_data and update_data["config"] is not None:
            config = update_data["config"]
            if hasattr(config, 'nome_impressora') and config.nome_impressora is not None:
                db_impressora.nome_impressora = config.nome_impressora
            if hasattr(config, 'fonte_nome') and config.fonte_nome is not None:
                db_impressora.fonte_nome = config.fonte_nome
            if hasattr(config, 'fonte_tamanho') and config.fonte_tamanho is not None:
                db_impressora.fonte_tamanho = config.fonte_tamanho
            if hasattr(config, 'espacamento_linha') and config.espacamento_linha is not None:
                db_impressora.espacamento_linha = config.espacamento_linha
            if hasattr(config, 'espacamento_item') and config.espacamento_item is not None:
                db_impressora.espacamento_item = config.espacamento_item
            if hasattr(config, 'nome_estabelecimento') and config.nome_estabelecimento is not None:
                db_impressora.nome_estabelecimento = config.nome_estabelecimento
            if hasattr(config, 'mensagem_rodape') and config.mensagem_rodape is not None:
                db_impressora.mensagem_rodape = config.mensagem_rodape
            if hasattr(config, 'formato_preco') and config.formato_preco is not None:
                db_impressora.formato_preco = config.formato_preco
            if hasattr(config, 'formato_total') and config.formato_total is not None:
                db_impressora.formato_total = config.formato_total

        self.db.commit()
        self.db.refresh(db_impressora)
        return db_impressora

    def delete_impressora(self, impressora_id: int) -> bool:
        db_impressora = self.get_impressora_by_id(impressora_id)
        if not db_impressora:
            return False

        self.db.delete(db_impressora)
        self.db.commit()
        return True

    def list_impressoras(self, skip: int = 0, limit: int = 100) -> List[ImpressoraModel]:
        return self.db.query(ImpressoraModel).offset(skip).limit(limit).all()
