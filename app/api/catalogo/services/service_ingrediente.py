from sqlalchemy.orm import Session
from typing import List

from app.api.catalogo.repositories.repo_ingrediente import IngredienteRepository
from app.api.catalogo.schemas.schema_ingrediente import (
    CriarIngredienteRequest,
    AtualizarIngredienteRequest,
    IngredienteResponse,
)


class IngredienteService:
    """Service para operações de negócio relacionadas a ingredientes."""

    def __init__(self, db: Session):
        self.repo = IngredienteRepository(db)

    def listar_ingredientes(self, empresa_id: int, apenas_ativos: bool = True) -> List[IngredienteResponse]:
        """Lista todos os ingredientes de uma empresa."""
        ingredientes = self.repo.listar_por_empresa(empresa_id, apenas_ativos)
        return [IngredienteResponse.model_validate(ing) for ing in ingredientes]

    def criar_ingrediente(self, req: CriarIngredienteRequest) -> IngredienteResponse:
        """Cria um novo ingrediente."""
        ingrediente = self.repo.criar_ingrediente(
            empresa_id=req.empresa_id,
            nome=req.nome,
            descricao=req.descricao,
            unidade_medida=req.unidade_medida,
            custo=req.custo,
            ativo=req.ativo,
        )
        return IngredienteResponse.model_validate(ingrediente)

    def buscar_por_id(self, ingrediente_id: int) -> IngredienteResponse:
        """Busca um ingrediente por ID."""
        ingrediente = self.repo.buscar_por_id(ingrediente_id)
        if not ingrediente:
            from fastapi import HTTPException, status
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingrediente não encontrado")
        return IngredienteResponse.model_validate(ingrediente)

    def atualizar_ingrediente(self, ingrediente_id: int, req: AtualizarIngredienteRequest) -> IngredienteResponse:
        """Atualiza um ingrediente existente."""
        data = {}
        if req.nome is not None:
            data["nome"] = req.nome
        if req.descricao is not None:
            data["descricao"] = req.descricao
        if req.unidade_medida is not None:
            data["unidade_medida"] = req.unidade_medida
        if req.custo is not None:
            data["custo"] = req.custo
        if req.ativo is not None:
            data["ativo"] = req.ativo

        ingrediente = self.repo.atualizar_ingrediente(ingrediente_id, **data)
        return IngredienteResponse.model_validate(ingrediente)

    def deletar_ingrediente(self, ingrediente_id: int):
        """Deleta um ingrediente. Só é possível deletar se não estiver vinculado a nenhuma receita."""
        self.repo.deletar_ingrediente(ingrediente_id)
        return {"message": "Ingrediente deletado com sucesso"}

