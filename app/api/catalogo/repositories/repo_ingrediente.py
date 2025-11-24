from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from decimal import Decimal

from app.api.catalogo.models.model_ingrediente import IngredienteModel
from app.api.catalogo.models.model_receita import ReceitaIngredienteModel


class IngredienteRepository:
    """Repository para operações CRUD de ingredientes."""

    def __init__(self, db: Session):
        self.db = db

    def criar_ingrediente(self, **data) -> IngredienteModel:
        """Cria um novo ingrediente."""
        obj = IngredienteModel(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def buscar_por_id(self, ingrediente_id: int) -> Optional[IngredienteModel]:
        """Busca um ingrediente por ID."""
        return self.db.query(IngredienteModel).filter_by(id=ingrediente_id).first()

    def listar_por_empresa(self, empresa_id: int, apenas_ativos: bool = True) -> List[IngredienteModel]:
        """Lista todos os ingredientes de uma empresa."""
        query = self.db.query(IngredienteModel).filter_by(empresa_id=empresa_id)
        if apenas_ativos:
            query = query.filter_by(ativo=True)
        return query.order_by(IngredienteModel.nome).all()

    def atualizar_ingrediente(self, ingrediente_id: int, **data) -> IngredienteModel:
        """Atualiza um ingrediente existente."""
        ingrediente = self.buscar_por_id(ingrediente_id)
        if not ingrediente:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingrediente não encontrado")
        
        for key, value in data.items():
            if value is not None:
                setattr(ingrediente, key, value)
        
        self.db.commit()
        self.db.refresh(ingrediente)
        return ingrediente

    def deletar_ingrediente(self, ingrediente_id: int):
        """Deleta um ingrediente. Só é possível deletar se não estiver vinculado a nenhuma receita."""
        ingrediente = self.buscar_por_id(ingrediente_id)
        if not ingrediente:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingrediente não encontrado")
        
        # Verifica se o ingrediente está vinculado a alguma receita
        receita_ingrediente = (
            self.db.query(ReceitaIngredienteModel)
            .filter_by(ingrediente_id=ingrediente_id)
            .first()
        )
        if receita_ingrediente:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Não é possível deletar ingrediente que está vinculado a uma ou mais receitas. Remova o ingrediente das receitas antes de deletar."
            )
        
        self.db.delete(ingrediente)
        self.db.commit()

    def ingrediente_esta_vinculado_receita(self, ingrediente_id: int) -> bool:
        """Verifica se um ingrediente está vinculado a alguma receita."""
        receita_ingrediente = (
            self.db.query(ReceitaIngredienteModel)
            .filter_by(ingrediente_id=ingrediente_id)
            .first()
        )
        return receita_ingrediente is not None

