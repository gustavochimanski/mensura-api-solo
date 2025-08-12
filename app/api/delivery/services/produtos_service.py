# app/api/delivery/services/produtos_service.py
from __future__ import annotations
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.delivery.repositories.produtos_dv_repo import ProdutoDeliveryRepository
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.delivery.schemas.produtos.produtos_dv_schema import (
    ProdutoListItem, CriarNovoProdutoResponse, CriarNovoProdutoRequest, ProdutoBaseDTO, ProdutoEmpDTO
)
from app.api.delivery.models.cadprod_dv_model import ProdutoDeliveryModel
from app.api.delivery.models.cadprod_emp_dv_model import ProdutoEmpDeliveryModel

class ProdutosDeliveryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProdutoDeliveryRepository(db)
        self.emp_repo = EmpresaRepository(db)

    def listar_paginado(self, empresa_id: int, page: int, limit: int, apenas_disponiveis: bool = False):
        offset = (page - 1) * limit
        produtos = self.repo.buscar_produtos_da_empresa(
            empresa_id, offset, limit,
            apenas_disponiveis=apenas_disponiveis,
            apenas_delivery=True,
        )
        total = self.repo.contar_total(
            empresa_id,
            apenas_disponiveis=apenas_disponiveis,
            apenas_delivery=True,
        )

        data = []
        for p in produtos:
            pe = next((x for x in p.produtos_empresa if x.empresa_id == empresa_id), None)
            if not pe:
                continue
            data.append(ProdutoListItem(
                cod_barras=p.cod_barras,
                descricao=p.descricao,
                imagem=p.imagem,
                preco_venda=float(pe.preco_venda),
                custo=(float(pe.custo) if pe.custo is not None else None),
                cod_categoria=p.cod_categoria,
                label_categoria=p.categoria.descricao if p.categoria else "",
                disponivel=pe.disponivel and p.ativo,
                exibir_delivery=pe.exibir_delivery,
            ))

        return {"data": data, "total": total, "page": page, "limit": limit, "has_more": offset + limit < total}

    def _empresa_or_404(self, empresa_id: int):
        if not self.emp_repo.get_empresa_by_id(empresa_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")

    def criar_novo_produto(self, empresa_id: int, req: CriarNovoProdutoRequest) -> CriarNovoProdutoResponse:
        self._empresa_or_404(empresa_id)

        if self.repo.buscar_por_cod_barras(req.cod_barras):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Produto já existe.")

        # produto base
        prod = self.repo.criar_produto(
            cod_barras=req.cod_barras,
            descricao=req.descricao,
            cod_categoria=req.cod_categoria,
            imagem=req.imagem,
            data_cadastro=req.data_cadastro,
            ativo=req.ativo,
            unidade_medida=req.unidade_medida
        )

        # vínculo com empresa
        pe = self.repo.upsert_produto_emp(
            empresa_id=empresa_id,
            cod_barras=prod.cod_barras,
            preco_venda=Decimal(str(req.preco_venda)),
            custo=(Decimal(str(req.custo)) if req.custo is not None else None),
            vitrine_id=req.vitrine_id,
            sku_empresa=req.sku_empresa,
            disponivel=req.disponivel,
            exibir_delivery=req.exibir_delivery
        )

        self.db.commit()
        self.db.refresh(prod)
        self.db.refresh(pe)

        return CriarNovoProdutoResponse(
            produto=ProdutoBaseDTO.model_validate(prod, from_attributes=True),
            produto_emp=ProdutoEmpDTO.model_validate(pe, from_attributes=True),
        )

    def atualizar_produto(self, empresa_id: int, cod_barras: str, req: CriarNovoProdutoRequest) -> CriarNovoProdutoResponse:
        self._empresa_or_404(empresa_id)

        prod = self.repo.buscar_por_cod_barras(cod_barras)
        if not prod:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado")

        # atualiza produto base (NÃO mexe em exibir_delivery aqui)
        self.repo.atualizar_produto(
            prod,
            descricao=req.descricao,
            cod_categoria=req.cod_categoria,
            imagem=req.imagem,
            ativo=req.ativo,
            unidade_medida=req.unidade_medida,
            data_cadastro=req.data_cadastro or prod.data_cadastro,
        )

        # upsert no vínculo
        pe = self.repo.upsert_produto_emp(
            empresa_id=empresa_id,
            cod_barras=cod_barras,
            preco_venda=Decimal(str(req.preco_venda)),
            custo=(Decimal(str(req.custo)) if req.custo is not None else None),
            vitrine_id=req.vitrine_id,
            sku_empresa=req.sku_empresa,
            disponivel=req.disponivel,
            exibir_delivery=req.exibir_delivery
        )

        self.db.commit()
        self.db.refresh(prod)
        self.db.refresh(pe)

        return CriarNovoProdutoResponse(
            produto=ProdutoBaseDTO.model_validate(prod, from_attributes=True),
            produto_emp=ProdutoEmpDTO.model_validate(pe, from_attributes=True),
        )

    def set_disponibilidade(self, empresa_id: int, cod_barras: str, on: bool):
        ok = self.repo.set_disponibilidade(empresa_id, cod_barras, on)
        if not ok:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vínculo produto x empresa não encontrado")
        self.db.commit()
        return {"ok": True}

    def deletar_produto(self, empresa_id: int, cod_barras: str):
        self._empresa_or_404(empresa_id)

        prod = self.repo.buscar_por_cod_barras(cod_barras)
        if not prod:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado")

        # Remove o vínculo produto x empresa
        if not self.repo.deletar_vinculo_produto_emp(empresa_id, cod_barras):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vínculo produto x empresa não encontrado")

        # Se não houver mais vínculos, remove o produto base
        # (consulta direta para garantir estado atualizado)
        remaining = self.repo.count_vinculos(cod_barras)
        if remaining == 0:
            self.repo.deletar_produto(cod_barras)  # só flush aqui

        self.db.commit()
        return {"ok": True, "message": "Produto deletado com sucesso"}
