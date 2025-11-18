from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from decimal import Decimal

from app.api.catalogo.receitas.models.model_ingrediente import IngredienteModel
from app.api.catalogo.receitas.repositories.repo_ingrediente import IngredienteRepository
from app.api.catalogo.receitas.schemas.schema_ingrediente import (
    IngredienteResponse,
    CriarIngredienteRequest,
    AtualizarIngredienteRequest,
)
from app.api.empresas.repositories.empresa_repo import EmpresaRepository


class IngredienteService:
    """Service para operações de ingredientes."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = IngredienteRepository(db)
        self.repo_empresa = EmpresaRepository(db)

    def _empresa_or_404(self, empresa_id: int):
        """Valida se a empresa existe."""
        empresa = self.repo_empresa.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada."
            )
        return empresa

    def criar_ingrediente(self, req: CriarIngredienteRequest) -> IngredienteResponse:
        """Cria um novo ingrediente."""
        self._empresa_or_404(req.empresa_id)
        
        ingrediente = self.repo.criar_ingrediente(
            empresa_id=req.empresa_id,
            nome=req.nome,
            descricao=req.descricao,
            unidade_medida=req.unidade_medida,
            custo=Decimal(str(req.custo)),
            ativo=req.ativo,
        )
        
        return IngredienteResponse.model_validate(ingrediente)

    def listar_ingredientes(self, empresa_id: int, apenas_ativos: bool = True) -> List[IngredienteResponse]:
        """Lista todos os ingredientes de uma empresa."""
        self._empresa_or_404(empresa_id)
        
        ingredientes = self.repo.listar_por_empresa(empresa_id, apenas_ativos)
        return [IngredienteResponse.model_validate(i) for i in ingredientes]

    def buscar_por_id(self, ingrediente_id: int) -> IngredienteResponse:
        """Busca um ingrediente por ID."""
        ingrediente = self.repo.buscar_por_id(ingrediente_id)
        if not ingrediente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ingrediente não encontrado."
            )
        return IngredienteResponse.model_validate(ingrediente)

    def atualizar_ingrediente(self, ingrediente_id: int, req: AtualizarIngredienteRequest) -> IngredienteResponse:
        """Atualiza um ingrediente existente."""
        update_data = {}
        if req.nome is not None:
            update_data["nome"] = req.nome
        if req.descricao is not None:
            update_data["descricao"] = req.descricao
        if req.unidade_medida is not None:
            update_data["unidade_medida"] = req.unidade_medida
        if req.custo is not None:
            update_data["custo"] = Decimal(str(req.custo))
        if req.ativo is not None:
            update_data["ativo"] = req.ativo
        
        ingrediente = self.repo.atualizar_ingrediente(ingrediente_id, **update_data)
        return IngredienteResponse.model_validate(ingrediente)

    def deletar_ingrediente(self, ingrediente_id: int):
        """Deleta um ingrediente."""
        self.repo.deletar_ingrediente(ingrediente_id)
        return {"message": "Ingrediente deletado com sucesso"}

