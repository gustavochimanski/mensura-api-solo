# app/api/delivery/services/service_produto.py
from __future__ import annotations
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.delivery.repositories.repo_produtos import ProdutoDeliveryRepository
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.mensura.schemas.schema_produtos import (
   CriarNovoProdutoResponse, CriarNovoProdutoRequest, ProdutoBaseDTO, ProdutoEmpDTO
)
from app.api.mensura.schemas.schema_produtos import ProdutoListItem
from app.utils.logger import logger
from app.utils.minio_client import update_file_to_minio, remover_arquivo_minio


class ProdutosDeliveryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProdutoDeliveryRepository(db)
        self.emp_repo = EmpresaRepository(db)

    def _empresa_or_404(self, empresa_id: int):
        if not self.emp_repo.get_empresa_by_id(empresa_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")


    def deletar_produto(self, empresa_id: int, cod_barras: str):
        self._empresa_or_404(empresa_id)

        prod = self.repo.buscar_por_cod_barras(cod_barras)
        if not prod:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado")

        # Captura a URL da imagem antes de deletar
        image_url = getattr(prod, "imagem", None)

        # Remove o vínculo produto x empresa
        if not self.repo.deletar_vinculo_produto_emp(empresa_id, cod_barras):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vínculo produto x empresa não encontrado")

        # Se não houver mais vínculos, remove o produto base
        # (consulta direta para garantir estado atualizado)
        remaining = self.repo.count_vinculos(cod_barras)
        if remaining == 0:
            self.repo.deletar_produto(cod_barras)  # só flush aqui
            
            # Remove a imagem do MinIO se existir
            if image_url:
                try:
                    remover_arquivo_minio(image_url)
                    logger.info(f"[Produtos] Imagem removida do MinIO: {image_url}")
                except Exception as e:
                    logger.warning(f"[Produtos] Falha ao remover imagem do MinIO: {e} | url={image_url}")

        self.db.commit()
        return {"ok": True, "message": "Produto deletado com sucesso"}

    def atualizar_produto(self, empresa_id: int, cod_barras: str, req: CriarNovoProdutoRequest, file=None) -> CriarNovoProdutoResponse:
        """
        Atualiza produto com ou sem upload de arquivo.
        Se file for fornecido, faz upload e remove arquivo antigo automaticamente.
        """
        self._empresa_or_404(empresa_id)

        prod = self.repo.buscar_por_cod_barras(cod_barras)
        if not prod:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado")

        # Se há arquivo, faz upload e remove o antigo
        if file:
            url_antiga = getattr(prod, "imagem", None)
            nova_url = update_file_to_minio(
                db=self.db,
                cod_empresa=empresa_id,
                file=file,
                slug="produtos",
                url_antiga=url_antiga
            )
            imagem_final = nova_url
        else:
            # Usa a imagem do request ou mantém a atual
            imagem_final = req.imagem or getattr(prod, "imagem", None)

        # atualiza produto base
        self.repo.atualizar_produto(
            prod,
            descricao=req.descricao,
            cod_categoria=req.cod_categoria,  # Pode ser None
            imagem=imagem_final,
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

        vitrine_id_resp = req.vitrine_id
        if vitrine_id_resp is None and pe.vitrines:
            vitrine_id_resp = pe.vitrines[0].id

        return CriarNovoProdutoResponse(
            produto=ProdutoBaseDTO.model_validate(prod, from_attributes=True),
            produto_emp=ProdutoEmpDTO(
                empresa_id=pe.empresa_id,
                cod_barras=pe.cod_barras,
                preco_venda=float(pe.preco_venda),
                custo=(float(pe.custo) if pe.custo is not None else None),
                vitrine_id=vitrine_id_resp,
                sku_empresa=pe.sku_empresa,
                disponivel=pe.disponivel,
                exibir_delivery=pe.exibir_delivery,
                created_at=pe.created_at,
                updated_at=pe.updated_at,
            ),
        )

    def _to_list_items(self, produtos, empresa_id: int) -> list[ProdutoListItem]:
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
                cod_categoria=p.cod_categoria,  # Pode ser None
                label_categoria=p.categoria.descricao if p.categoria else None,
                disponivel=pe.disponivel and p.ativo,
                exibir_delivery=pe.exibir_delivery,
            ))
        return data

    def buscar_paginado(
        self,
        *,
        empresa_id: int,
        q: Optional[str],
        page: int,
        limit: int,
        apenas_disponiveis: bool = False,
        apenas_delivery: bool = True,
    ):
        offset = (page - 1) * limit
        produtos = self.repo.search_produtos_da_empresa(
            empresa_id=empresa_id,
            q=q,
            offset=offset,
            limit=limit,
            apenas_disponiveis=apenas_disponiveis,
            apenas_delivery=apenas_delivery,
        )
        total = self.repo.count_search_total(
            empresa_id=empresa_id,
            q=q,
            apenas_disponiveis=apenas_disponiveis,
            apenas_delivery=apenas_delivery,
        )
        data = self._to_list_items(produtos, empresa_id)
        return {"data": data, "total": total, "page": page, "limit": limit, "has_more": offset + limit < total}
