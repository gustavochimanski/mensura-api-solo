from decimal import Decimal

from fastapi import HTTPException
from rich import status
from sqlalchemy.orm import Session

from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.mensura.repositories.repo_produto import ProdutoMensuraRepository
from app.api.mensura.schemas.schema_produtos import ProdutoListItem, CriarNovoProdutoResponse, ProdutoEmpDTO, \
    ProdutoBaseDTO, CriarNovoProdutoRequest


class ProdutosMensuraService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProdutoMensuraRepository(db)
        self.empresa_repo = EmpresaRepository(db)

    def _empresa_or_404(self, empresa_id: int):
        empresa = self.empresa_repo.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada."
            )
        return empresa

    def criar_novo_produto(self, empresa_id: int, req: CriarNovoProdutoRequest) -> CriarNovoProdutoResponse:
        # garante que a empresa existe antes de prosseguir
        self._empresa_or_404(empresa_id)

        if self.repo.buscar_por_cod_barras(req.cod_barras):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Produto já existe.")

        # produto base (sem categoria)
        prod = self.repo.criar_produto(
            cod_barras=req.cod_barras,
            descricao=req.descricao,
            imagem=req.imagem,
            data_cadastro=req.data_cadastro,
            ativo=req.ativo,
            unidade_medida=req.unidade_medida,
        )

        # vínculo com empresa (sem vitrine)
        pe = self.repo.upsert_produto_emp(
            empresa_id=empresa_id,
            cod_barras=prod.cod_barras,
            preco_venda=Decimal(str(req.preco_venda)),
            custo=(Decimal(str(req.custo)) if req.custo is not None else None),
            sku_empresa=req.sku_empresa,
            disponivel=req.disponivel,
            exibir_delivery=req.exibir_delivery,
        )

        self.db.commit()
        self.db.refresh(prod)
        self.db.refresh(pe)

        return CriarNovoProdutoResponse(
            produto=ProdutoBaseDTO.model_validate(prod, from_attributes=True),
            produto_emp=ProdutoEmpDTO(
                empresa_id=pe.empresa_id,
                cod_barras=pe.cod_barras,
                preco_venda=float(pe.preco_venda),
                custo=(float(pe.custo) if pe.custo is not None else None),
                vitrine_id=None,
                sku_empresa=pe.sku_empresa,
                disponivel=pe.disponivel,
                exibir_delivery=pe.exibir_delivery,
                created_at=pe.created_at,
                updated_at=pe.updated_at,
            ),
        )

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
                # cod_categoria=p.cod_categoria,  # Removido
                # label_categoria=p.categoria.descricao if p.categoria else None,  # Removido
                disponivel=pe.disponivel and p.ativo,
                exibir_delivery=pe.exibir_delivery,
            ))

        return {"data": data, "total": total, "page": page, "limit": limit, "has_more": offset + limit < total}