from __future__ import annotations
from typing import Optional, List
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from app.utils.slug_utils import make_slug

from app.api.cardapio.models.model_categoria_dv import CategoriaDeliveryModel
from app.api.cadastros.schemas.schema_categoria import CategoriaDeliveryIn


class CategoriaDeliveryRepository:
    def __init__(self, db: Session):
        self.db = db

    # -------- CRUD --------
    def create(self, data: CategoriaDeliveryIn) -> CategoriaDeliveryModel:
        from app.utils.logger import logger
        
        logger.info(f"[Categorias] Criando categoria no repositório - descricao={data.descricao}, imagem={data.imagem}, slug={data.slug}")
        
        # sempre gera o slug a partir da descrição (ignora o slug fornecido)
        slug_value = make_slug(data.descricao)
        logger.info(f"[Categorias] Slug gerado: {slug_value}")

        existe = self.db.query(CategoriaDeliveryModel).filter_by(slug=slug_value).first()
        if existe:
            logger.warning(f"[Categorias] Slug já existe: {slug_value}")
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Já existe uma categoria com esse slug (gerado automaticamente)."
            )

        posicao = data.posicao
        if posicao is None:
            max_posicao = (
                self.db.query(func.max(CategoriaDeliveryModel.posicao))
                .filter(CategoriaDeliveryModel.parent_id == data.parent_id)
                .scalar()
            )
            posicao = (max_posicao or 0) + 1

        nova = CategoriaDeliveryModel(
            descricao=data.descricao,
            slug=slug_value,
            parent_id=data.parent_id,
            imagem=data.imagem,
            posicao=posicao
        )
        
        logger.info(f"[Categorias] Objeto categoria criado - imagem={nova.imagem}, slug={nova.slug}")
        
        self.db.add(nova)
        try:
            self.db.commit()
            self.db.refresh(nova)
            logger.info(f"[Categorias] Categoria salva no banco - id={nova.id}, imagem={nova.imagem}, slug={nova.slug}")
            return nova
        except Exception as e:
            logger.error(f"[Categorias] Erro ao salvar categoria no banco: {e}")
            self.db.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro ao criar categoria")

    def list_by_parent(self, parent_id: Optional[int]) -> List[CategoriaDeliveryModel]:
        stmt = (
            select(CategoriaDeliveryModel)
            .where(CategoriaDeliveryModel.parent_id == parent_id)
            .order_by(CategoriaDeliveryModel.posicao)
        )
        return self.db.execute(stmt).scalars().all()

    def get_by_id(self, cat_id: int) -> CategoriaDeliveryModel:
        cat = self.db.query(CategoriaDeliveryModel).filter_by(id=cat_id).first()
        if not cat:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoria não encontrada")
        return cat

    def update(self, cat_id: int, update_data: dict) -> CategoriaDeliveryModel:
        from app.utils.logger import logger
        
        logger.info(f"[Categorias] Atualizando categoria - id={cat_id}, update_data={update_data}")
        
        cat = self.get_by_id(cat_id)
        if not cat:
            logger.error(f"[Categorias] Categoria não encontrada - id={cat_id}")
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoria não encontrada")

        # 1) Slug NUNCA vem do payload: se vier, ignoramos
        update_data.pop("slug", None)

        # 2) Se veio 'descricao', sincroniza o slug com ela
        if "descricao" in update_data and update_data["descricao"]:
            novo_slug = make_slug(update_data["descricao"])

            # unicidade do slug (exclui a própria categoria)
            existe = (
                self.db.query(CategoriaDeliveryModel)
                .filter(
                    CategoriaDeliveryModel.slug == novo_slug,
                    CategoriaDeliveryModel.id != cat_id
                )
                .first()
            )
            if existe:
                logger.warning(f"[Categorias] Slug já existe: {novo_slug}")
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Já existe uma categoria com esse slug (gerado a partir da descrição)."
                )

            cat.slug = novo_slug

        # 3) Atribui os demais campos permitidos
        for key in ("descricao", "parent_id", "imagem", "posicao"):
            if key in update_data and update_data[key] is not None:
                logger.info(f"[Categorias] Atualizando campo {key}: {getattr(cat, key)} -> {update_data[key]}")
                setattr(cat, key, update_data[key])

        try:
            self.db.commit()
            logger.info(f"[Categorias] Categoria atualizada com sucesso - id={cat_id}, imagem={cat.imagem}")
        except IntegrityError as e:
            logger.error(f"[Categorias] Erro de integridade ao atualizar categoria: {e}")
            self.db.rollback()
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Violação de unicidade/constraint ao atualizar categoria"
            )
        except Exception as e:
            logger.error(f"[Categorias] Erro ao atualizar categoria: {e}")
            self.db.rollback()
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Erro ao atualizar categoria"
            )

        self.db.refresh(cat)
        return cat

    def delete(self, cat_id: int) -> None:
        cat = self.get_by_id(cat_id)
        self.db.delete(cat)
        self.db.commit()

    # -------- Ordering --------
    def move_right(self, cat_id: int) -> CategoriaDeliveryModel:
        cat = self.get_by_id(cat_id)
        irmas = (
            self.db.query(CategoriaDeliveryModel)
            .filter_by(parent_id=cat.parent_id)
            .order_by(CategoriaDeliveryModel.posicao)
            .all()
        )
        idx = next((i for i, c in enumerate(irmas) if c.id == cat_id), None)
        if idx is None or idx == len(irmas) - 1:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Não é possível mover para a direita")
        proxima = irmas[idx + 1]
        cat.posicao, proxima.posicao = proxima.posicao, cat.posicao
        try:
            self.db.commit()
            self.db.refresh(cat)
            return cat
        except Exception:
            self.db.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro ao mover categoria para a direita")

    def move_left(self, cat_id: int) -> CategoriaDeliveryModel:
        cat = self.get_by_id(cat_id)
        irmas = (
            self.db.query(CategoriaDeliveryModel)
            .filter_by(parent_id=cat.parent_id)
            .order_by(CategoriaDeliveryModel.posicao)
            .all()
        )
        idx = next((i for i, c in enumerate(irmas) if c.id == cat_id), None)
        if idx is None or idx == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Não é possível mover para a esquerda")
        anterior = irmas[idx - 1]
        cat.posicao, anterior.posicao = anterior.posicao, cat.posicao
        try:
            self.db.commit()
            self.db.refresh(cat)
            return cat
        except Exception:
            self.db.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro ao mover categoria para a esquerda")

    # -------- SEARCH GLOBAL --------
    def search_all(
        self, q: Optional[str], limit: int = 30, offset: int = 0
    ) -> List[CategoriaDeliveryModel]:
        """
        Busca em TODAS as categorias (raiz e filhas), com filtro por descrição/slug.
        Ordena por: raiz primeiro (parent_id NULL), depois posicao.
        Requer extensão unaccent para acento-insensível (opcional).
        """
        base = (
            self.db.query(CategoriaDeliveryModel)
            .options(joinedload(CategoriaDeliveryModel.parent))
            .order_by(
                # raiz primeiro
                CategoriaDeliveryModel.parent_id.isnot(None),
                CategoriaDeliveryModel.posicao
            )
        )

        if q and q.strip():
            term = f"%{q.strip()}%"
            # Tenta unaccent se disponível; caso não, cai no ILIKE normal
            try:
                cond = or_(
                    func.unaccent(CategoriaDeliveryModel.descricao).ilike(func.unaccent(term)),
                    func.unaccent(CategoriaDeliveryModel.slug).ilike(func.unaccent(term)),
                )
                base = base.filter(cond)
            except Exception:
                cond = or_(
                    CategoriaDeliveryModel.descricao.ilike(term),
                    CategoriaDeliveryModel.slug.ilike(term),
                )
                base = base.filter(cond)

        return base.offset(offset).limit(limit).all()
