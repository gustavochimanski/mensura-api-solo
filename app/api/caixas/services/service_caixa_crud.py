from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.caixas.repositories.repo_caixa_crud import CaixaCRUDRepository
from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.caixas.schemas.schema_caixa_crud import (
    CaixaCreate,
    CaixaUpdate,
    CaixaResponse
)
from app.api.caixas.models.model_caixa import CaixaModel
from app.utils.logger import logger


class CaixaCRUDService:
    """Service para CRUD de caixas cadastrados"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = CaixaCRUDRepository(db)
        self.repo_empresa = EmpresaRepository(db)

    def _empresa_or_404(self, empresa_id: int):
        """Valida se empresa existe"""
        empresa = self.repo_empresa.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada"
            )
        return empresa

    def create(self, data: CaixaCreate) -> CaixaResponse:
        """Cria um novo caixa"""
        self._empresa_or_404(data.empresa_id)
        
        caixa = self.repo.create(
            empresa_id=data.empresa_id,
            nome=data.nome,
            descricao=data.descricao,
            ativo=data.ativo
        )
        
        logger.info(f"[Caixa] Criado caixa_id={caixa.id} empresa_id={data.empresa_id} nome={caixa.nome}")
        return self._caixa_to_response(caixa)

    def get_by_id(self, caixa_id: int, empresa_id: Optional[int] = None) -> CaixaResponse:
        """Busca um caixa por ID, opcionalmente validando empresa"""
        caixa = self.repo.get_by_id(caixa_id)
        if not caixa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Caixa não encontrado"
            )
        
        # Valida se o caixa pertence à empresa
        if empresa_id and caixa.empresa_id != empresa_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Caixa não pertence à empresa informada"
            )
        
        return self._caixa_to_response(caixa)

    def list(
        self,
        empresa_id: Optional[int] = None,
        ativo: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[CaixaResponse]:
        """Lista caixas com filtros"""
        if empresa_id:
            self._empresa_or_404(empresa_id)
        
        caixas = self.repo.list(
            empresa_id=empresa_id,
            ativo=ativo,
            skip=skip,
            limit=limit
        )
        
        return [self._caixa_to_response(c) for c in caixas]

    def update(self, caixa_id: int, data: CaixaUpdate, empresa_id: Optional[int] = None) -> CaixaResponse:
        """Atualiza um caixa"""
        caixa = self.repo.get_by_id(caixa_id)
        if not caixa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Caixa não encontrado"
            )
        
        # Valida se o caixa pertence à empresa
        if empresa_id and caixa.empresa_id != empresa_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Caixa não pertence à empresa informada"
            )
        
        update_data = data.model_dump(exclude_unset=True)
        caixa = self.repo.update(caixa, **update_data)
        
        logger.info(f"[Caixa] Atualizado caixa_id={caixa_id}")
        return self._caixa_to_response(caixa)

    def delete(self, caixa_id: int, empresa_id: Optional[int] = None) -> None:
        """Remove um caixa (soft delete)"""
        caixa = self.repo.get_by_id(caixa_id)
        if not caixa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Caixa não encontrado"
            )
        
        # Valida se o caixa pertence à empresa
        if empresa_id and caixa.empresa_id != empresa_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Caixa não pertence à empresa informada"
            )
        
        self.repo.delete(caixa)
        logger.info(f"[Caixa] Removido caixa_id={caixa_id}")

    def _caixa_to_response(self, caixa: CaixaModel) -> CaixaResponse:
        """Converte model para response"""
        return CaixaResponse(
            id=caixa.id,
            empresa_id=caixa.empresa_id,
            nome=caixa.nome,
            descricao=caixa.descricao,
            ativo=caixa.ativo,
            created_at=caixa.created_at,
            updated_at=caixa.updated_at,
            empresa_nome=caixa.empresa.nome if caixa.empresa else None,
        )

