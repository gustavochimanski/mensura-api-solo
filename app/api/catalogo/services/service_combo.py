from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException, status, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.catalogo.repositories.repo_combo import ComboRepository
from app.api.catalogo.schemas.schema_combo import (
    CriarComboRequest,
    AtualizarComboRequest,
    ComboDTO,
    ComboItemDTO,
    ListaCombosResponse,
)
from app.api.pedidos.models.model_pedido_item_unificado import PedidoItemUnificadoModel
from app.utils.minio_client import upload_file_to_minio, update_file_to_minio


class CombosService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ComboRepository(db)
        self.empresa_repo = EmpresaRepository(db)

    def _empresa_or_404(self, empresa_id: int):
        empresa = self.empresa_repo.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada.")
        return empresa

    def criar(self, req: CriarComboRequest, imagem: UploadFile | None = None) -> ComboDTO:
        self._empresa_or_404(req.empresa_id)

        imagem_url = None
        if imagem is not None:
            imagem_url = upload_file_to_minio(self.db, req.empresa_id, imagem, "combos")

        combo = self.repo.criar_combo(
            empresa_id=req.empresa_id,
            titulo=req.titulo,
            descricao=req.descricao,
            preco_total=Decimal(str(req.preco_total)),
            custo_total=(Decimal(str(req.custo_total)) if req.custo_total is not None else None),
            ativo=req.ativo,
            imagem_url=imagem_url,
            itens=[
                {
                    "produto_cod_barras": it.produto_cod_barras if it.produto_cod_barras else None,
                    "receita_id": it.receita_id if it.receita_id else None,
                    "quantidade": it.quantidade
                } for it in req.itens
            ],
        )
        self.db.commit()
        self.db.refresh(combo)
        return self._to_dto(combo)

    def atualizar(self, combo_id: int, req: AtualizarComboRequest, imagem: UploadFile | None = None) -> ComboDTO:
        combo = self.repo.get_by_id(combo_id)
        if not combo:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Combo não encontrado.")

        imagem_url = None
        if imagem is not None:
            imagem_url = update_file_to_minio(self.db, combo.empresa_id, imagem, "combos", url_antiga=combo.imagem)

        combo = self.repo.atualizar_combo(
            combo,
            titulo=req.titulo,
            descricao=req.descricao,
            preco_total=(Decimal(str(req.preco_total)) if req.preco_total is not None else None),
            custo_total=(Decimal(str(req.custo_total)) if req.custo_total is not None else None),
            ativo=req.ativo,
            imagem_url=imagem_url,
            itens=(
                [
                    {
                        "produto_cod_barras": it.produto_cod_barras if it.produto_cod_barras else None,
                        "receita_id": it.receita_id if it.receita_id else None,
                        "quantidade": it.quantidade
                    } for it in (req.itens or [])
                ]
                if req.itens is not None else None
            ),
        )
        self.db.commit()
        self.db.refresh(combo)
        return self._to_dto(combo)

    def deletar(self, combo_id: int) -> None:
        combo = self.repo.get_by_id(combo_id)
        if not combo:
            return
        
        # Verificar se há pedidos_itens referenciando o combo
        pedidos_itens_count = self.db.query(func.count(PedidoItemUnificadoModel.id))\
            .filter(PedidoItemUnificadoModel.combo_id == combo_id)\
            .scalar() or 0
        
        if pedidos_itens_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não é possível deletar combo que está sendo referenciado por {pedidos_itens_count} item(ns) de pedido(s)"
            )
        
        self.repo.deletar_combo(combo)
        self.db.commit()

    def listar(self, empresa_id: int, page: int, limit: int, search: Optional[str] = None) -> ListaCombosResponse:
        """
        Lista combos de uma empresa com paginação e busca opcional.

        - `search`: termo aplicado em título/descrição (filtrado no banco).
        """
        self._empresa_or_404(empresa_id)
        offset = (page - 1) * limit
        combos = self.repo.list_paginado(empresa_id, offset, limit, search=search)
        total = self.repo.count_total(empresa_id, search=search)
        return ListaCombosResponse(
            data=[self._to_dto(c) for c in combos],
            total=total,
            page=page,
            limit=limit,
            has_more=offset + limit < total,
        )

    def obter(self, combo_id: int) -> ComboDTO:
        combo = self.repo.get_by_id(combo_id)
        if not combo:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Combo não encontrado.")
        return self._to_dto(combo)

    @staticmethod
    def _to_dto(combo) -> ComboDTO:
        return ComboDTO(
            id=combo.id,
            empresa_id=combo.empresa_id,
            titulo=combo.titulo or "",
            descricao=combo.descricao,
            preco_total=float(combo.preco_total),
            custo_total=(float(combo.custo_total) if combo.custo_total is not None else None),
            ativo=combo.ativo,
            imagem=combo.imagem,
            itens=[
                ComboItemDTO(
                    produto_cod_barras=i.produto_cod_barras,
                    receita_id=i.receita_id,
                    quantidade=i.quantidade
                ) for i in combo.itens
            ],
            created_at=combo.created_at,
            updated_at=combo.updated_at,
        )

