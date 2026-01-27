from __future__ import annotations

from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.cardapio.models.model_vitrine import VitrinesLandingpageStoreModel
from app.api.cardapio.repositories.repo_vitrines_landingpage_store import VitrineLandingpageStoreRepository
from app.api.cardapio.schemas.schema_vitrine import CriarVitrineRequest, AtualizarVitrineRequest
from app.api.catalogo.models.model_receita import ReceitaModel
from app.utils.logger import logger


class VitrinesLandingpageStoreService:
    """
    Service (landingpage_store): validações e tradução para HTTP.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = VitrineLandingpageStoreRepository(db)

    def search(
        self,
        *,
        empresa_id: int,
        q: Optional[str],
        is_home: Optional[bool],
        limit: int,
        offset: int,
    ) -> List[VitrinesLandingpageStoreModel]:
        return self.repo.search(
            empresa_id=empresa_id,
            q=q,
            is_home=is_home,
            limit=limit,
            offset=offset,
        )

    def create(self, req: CriarVitrineRequest) -> VitrinesLandingpageStoreModel:
        # cod_categoria não é aplicável na landingpage_store
        if req.cod_categoria is not None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="cod_categoria não é permitido quando landingpage_true=true",
            )
        try:
            return self.repo.create(
                empresa_id=req.empresa_id,
                titulo=req.titulo,
                is_home=bool(req.is_home),
            )
        except IntegrityError as e:
            self.db.rollback()
            error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"[VitrinesLandingpageStore] Erro de integridade ao criar vitrine: {error_str}")
            logger.error(f"[VitrinesLandingpageStore] Dados recebidos: empresa_id={req.empresa_id}, titulo={req.titulo}")
            
            # Verifica se é duplicidade de slug
            if 'uq_vitrine_landing_slug_empresa' in error_str or 'slug' in error_str.lower():
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=f"Já existe uma vitrine com o título '{req.titulo}' para esta empresa. Tente um título diferente."
                )
            
            # Verifica se é erro de chave estrangeira (empresa não existe)
            if 'foreign key' in error_str.lower() or 'violates foreign key constraint' in error_str.lower():
                if 'empresa' in error_str.lower():
                    raise HTTPException(
                        status.HTTP_404_NOT_FOUND,
                        detail=f"Empresa com ID {req.empresa_id} não encontrada"
                    )
            
            # Outros erros de integridade
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Conflito de dados ao criar vitrine: {error_str}"
            )

    def update(
        self, vitrine_id: int, req: AtualizarVitrineRequest, *, empresa_id: int
    ) -> VitrinesLandingpageStoreModel:
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")

        if req.cod_categoria is not None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="cod_categoria não é permitido quando landingpage_true=true",
            )

        try:
            return self.repo.update(
                v,
                titulo=req.titulo,
                ordem=req.ordem,
                is_home=req.is_home,
            )
        except IntegrityError as e:
            self.db.rollback()
            error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"[VitrinesLandingpageStore] Erro de integridade ao atualizar vitrine: {error_str}")
            logger.error(f"[VitrinesLandingpageStore] Dados recebidos: vitrine_id={vitrine_id}, titulo={req.titulo}")
            
            # Verifica se é duplicidade de slug
            if 'uq_vitrine_landing_slug_empresa' in error_str or 'slug' in error_str.lower():
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=f"Já existe uma vitrine com o título '{req.titulo}' para esta empresa. Tente um título diferente."
                )
            
            # Outros erros de integridade
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Conflito de dados ao atualizar vitrine: {error_str}"
            )

    def delete(self, vitrine_id: int, *, empresa_id: int) -> None:
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        if self.repo.has_vinculos(vitrine_id):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Não é possível excluir. Existem produtos vinculados.",
            )
        self.repo.delete(v)

    def set_is_home(self, vitrine_id: int, is_home: bool, *, empresa_id: int) -> VitrinesLandingpageStoreModel:
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        return self.repo.set_is_home(v, is_home)

    def vincular_produto(self, vitrine_id: int, empresa_id: int, cod_barras: str):
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        if not self.repo.exists_prod_emp(empresa_id=empresa_id, cod_barras=cod_barras):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Produto da empresa não encontrado")
        ok = self.repo.vincular_produto(vitrine_id=vitrine_id, cod_barras=cod_barras)
        if not ok:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Falha ao vincular produto")
        return {"ok": True}

    def desvincular_produto(self, vitrine_id: int, empresa_id: int, cod_barras: str):
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        if not self.repo.exists_prod_emp(empresa_id=empresa_id, cod_barras=cod_barras):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Produto da empresa não encontrado")
        ok = self.repo.desvincular_produto(vitrine_id=vitrine_id, cod_barras=cod_barras)
        if not ok:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Produto não estava vinculado")
        return {"ok": True}

    def vincular_combo(self, vitrine_id: int, combo_id: int, *, empresa_id: int):
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        ok = self.repo.vincular_combo(vitrine_id=vitrine_id, combo_id=combo_id)
        if not ok:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Falha ao vincular combo")
        return {"ok": True}

    def desvincular_combo(self, vitrine_id: int, combo_id: int, *, empresa_id: int):
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        ok = self.repo.desvincular_combo(vitrine_id=vitrine_id, combo_id=combo_id)
        if not ok:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Combo não estava vinculado")
        return {"ok": True}

    def vincular_receita(self, vitrine_id: int, receita_id: int, *, empresa_id: int):
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        receita = self.db.query(ReceitaModel).filter(ReceitaModel.id == receita_id).first()
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Receita não encontrada")
        ok = self.repo.vincular_receita(vitrine_id=vitrine_id, receita_id=receita_id)
        if not ok:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Falha ao vincular receita")
        return {"ok": True}

    def desvincular_receita(self, vitrine_id: int, receita_id: int, *, empresa_id: int):
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        ok = self.repo.desvincular_receita(vitrine_id=vitrine_id, receita_id=receita_id)
        if not ok:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Receita não estava vinculada")
        return {"ok": True}

