from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status
from decimal import Decimal

from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.catalogo.receitas.models.model_ingrediente import IngredienteModel
from app.api.catalogo.models.model_receita import ReceitaIngredienteModel, ReceitaAdicionalModel, ReceitaModel
from app.api.catalogo.schemas.schema_receitas import (
    ReceitaIngredienteIn,
    AdicionalIn,
    ReceitaIn,
    ReceitaUpdate,
)


class ReceitasRepository:
    def __init__(self, db: Session):
        self.db = db

    # Receitas - CRUD completo
    def create_receita(self, data: ReceitaIn) -> ReceitaModel:
        receita = ReceitaModel(
            empresa_id=data.empresa_id,
            nome=data.nome,
            descricao=data.descricao,
            preco_venda=data.preco_venda,
            imagem=data.imagem,
            ativo=data.ativo,
            disponivel=data.disponivel,
        )
        self.db.add(receita)
        self.db.commit()
        self.db.refresh(receita)
        return receita

    def get_receita_by_id(self, receita_id: int) -> Optional[ReceitaModel]:
        return self.db.query(ReceitaModel).filter_by(id=receita_id).first()

    def list_receitas(self, empresa_id: Optional[int] = None, ativo: Optional[bool] = None) -> List[ReceitaModel]:
        query = self.db.query(ReceitaModel)
        
        if empresa_id is not None:
            query = query.filter_by(empresa_id=empresa_id)
        
        if ativo is not None:
            query = query.filter_by(ativo=ativo)
        
        return query.order_by(ReceitaModel.nome).all()
    
    def list_receitas_com_ingredientes(self, empresa_id: Optional[int] = None, ativo: Optional[bool] = None) -> List[ReceitaModel]:
        """Lista receitas com seus ingredientes carregados"""
        query = (
            self.db.query(ReceitaModel)
            .options(joinedload(ReceitaModel.ingredientes).joinedload(ReceitaIngredienteModel.ingrediente))
        )
        
        if empresa_id is not None:
            query = query.filter_by(empresa_id=empresa_id)
        
        if ativo is not None:
            query = query.filter_by(ativo=ativo)
        
        return query.order_by(ReceitaModel.nome).all()

    def update_receita(self, receita_id: int, data: ReceitaUpdate) -> ReceitaModel:
        receita = self.get_receita_by_id(receita_id)
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")

        if data.nome is not None:
            receita.nome = data.nome
        if data.descricao is not None:
            receita.descricao = data.descricao
        if data.preco_venda is not None:
            receita.preco_venda = data.preco_venda
        if data.imagem is not None:
            receita.imagem = data.imagem
        if data.ativo is not None:
            receita.ativo = data.ativo
        if data.disponivel is not None:
            receita.disponivel = data.disponivel

        self.db.add(receita)
        self.db.commit()
        self.db.refresh(receita)
        return receita

    def delete_receita(self, receita_id: int) -> None:
        receita = self.get_receita_by_id(receita_id)
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")
        
        self.db.delete(receita)
        self.db.commit()

    # Ingredientes - Usa ReceitaIngredienteModel (receita_ingrediente)
    # Relacionamento N:N (um ingrediente pode estar em várias receitas, uma receita pode ter vários ingredientes)
    def add_ingrediente(self, data: ReceitaIngredienteIn) -> ReceitaIngredienteModel:
        # Verifica se a receita existe
        receita = self.get_receita_by_id(data.receita_id)
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")
        
        # Verifica se o ingrediente existe
        ingrediente = self.db.query(IngredienteModel).filter_by(id=data.ingrediente_id).first()
        if not ingrediente:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingrediente não encontrado")

        # Verifica se já existe na mesma receita (evita duplicatas)
        exists_mesma_receita = (
            self.db.query(ReceitaIngredienteModel)
            .filter_by(receita_id=data.receita_id, ingrediente_id=data.ingrediente_id)
            .first()
        )
        if exists_mesma_receita:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ingrediente já cadastrado nesta receita")

        obj = ReceitaIngredienteModel(
            receita_id=data.receita_id,
            ingrediente_id=data.ingrediente_id,
            quantidade=data.quantidade,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def list_ingredientes(self, receita_id: int) -> List[ReceitaIngredienteModel]:
        # Verifica se a receita existe
        receita = self.get_receita_by_id(receita_id)
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")
        
        return (
            self.db.query(ReceitaIngredienteModel)
            .options(joinedload(ReceitaIngredienteModel.ingrediente))
            .filter(ReceitaIngredienteModel.receita_id == receita_id)
            .all()
        )

    def update_ingrediente(self, receita_ingrediente_id: int, quantidade: float | None) -> ReceitaIngredienteModel:
        obj = self.db.query(ReceitaIngredienteModel).filter_by(id=receita_ingrediente_id).first()
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingrediente não encontrado na receita")
        if quantidade is not None:
            obj.quantidade = quantidade
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def remove_ingrediente(self, ingrediente_id: int) -> None:
        obj = self.db.query(ReceitaIngredienteModel).filter_by(id=ingrediente_id).first()
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingrediente não encontrado")
        self.db.delete(obj)
        self.db.commit()

    # Adicionais - Usa ReceitaAdicionalModel (receita_adicional)
    def add_adicional(self, data: AdicionalIn) -> ReceitaAdicionalModel:
        # Verifica se a receita existe
        receita = self.get_receita_by_id(data.receita_id)
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")
        
        # Verifica se o adicional existe
        add = self.db.query(ProdutoModel).filter_by(cod_barras=data.adicional_cod_barras).first()
        if not add:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Adicional inválido")

        # Verifica se já existe
        exists = (
            self.db.query(ReceitaAdicionalModel)
            .filter_by(receita_id=data.receita_id, adicional_cod_barras=data.adicional_cod_barras)
            .first()
        )
        if exists:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Adicional já cadastrado nesta receita")

        obj = ReceitaAdicionalModel(
            receita_id=data.receita_id,
            adicional_cod_barras=data.adicional_cod_barras,
            preco=data.preco,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def list_adicionais(self, receita_id: int) -> List[ReceitaAdicionalModel]:
        # Verifica se a receita existe
        receita = self.get_receita_by_id(receita_id)
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")
        
        return (
            self.db.query(ReceitaAdicionalModel)
            .filter(ReceitaAdicionalModel.receita_id == receita_id)
            .all()
        )

    def update_adicional(self, adicional_id: int, preco) -> ReceitaAdicionalModel:
        obj = self.db.query(ReceitaAdicionalModel).filter_by(id=adicional_id).first()
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Adicional não encontrado")
        obj.preco = preco
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def remove_adicional(self, adicional_id: int) -> None:
        obj = self.db.query(ReceitaAdicionalModel).filter_by(id=adicional_id).first()
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Adicional não encontrado")
        self.db.delete(obj)
        self.db.commit()

    def receita_tem_ingredientes(self, receita_id: int) -> bool:
        """Verifica se uma receita possui ingredientes cadastrados"""
        receita = self.get_receita_by_id(receita_id)
        if not receita:
            return False
        
        count = (
            self.db.query(func.count(ReceitaIngredienteModel.id))
            .filter(ReceitaIngredienteModel.receita_id == receita_id)
            .scalar()
        )
        return count > 0 if count else False

    def produto_tem_receita(self, produto_cod_barras: str) -> bool:
        """
        Verifica se um produto está associado a alguma receita.
        Com a nova estrutura, isso verifica se o produto é usado como adicional em alguma receita.
        """
        count = (
            self.db.query(func.count(ReceitaAdicionalModel.id))
            .filter(ReceitaAdicionalModel.adicional_cod_barras == produto_cod_barras)
            .scalar()
        )
        return count > 0 if count else False

