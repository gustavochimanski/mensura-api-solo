# services/produtos_service.py
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.delivery.repositories.produtos_dv_repo import ProdutoDeliveryRepository
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.delivery.schemas.produtos.produtos_dv_schema import ProdutoListItem, CriarNovoProdutoResponse, \
    CriarNovoProdutoRequest
from app.api.delivery.models.cadprod_dv_model import ProdutoDeliveryModel
from app.api.delivery.models.cadprod_emp_dv_model import ProdutoEmpDeliveryModel


class ProdutosDeliveryService:
    def __init__(self, db: Session):
        self.db = db
        self.produto_repo = ProdutoDeliveryRepository(db)
        self.emp_repo = EmpresaRepository(db)

    def listar_paginado(self, cod_empresa: int, page: int, limit: int):
        offset = (page - 1) * limit
        produtos = self.produto_repo.buscar_produtos_da_empresa(cod_empresa, offset, limit)
        total = self.produto_repo.contar_total(cod_empresa)

        data = []
        for p in produtos:
            pe = next(pe for pe in p.produtos_empresa if pe.empresa == cod_empresa)
            data.append(ProdutoListItem(
                cod_barras=p.cod_barras,
                descricao=p.descricao,
                imagem=p.imagem,
                preco_venda=float(pe.preco_venda),
                custo=float(pe.custo or 0),
                cod_categoria=p.cod_categoria,
                label_categoria=p.categoria.descricao if p.categoria else ""
            ))

        return {"data": data, "total": total, "page": page, "limit": limit, "has_more": offset + limit < total}

    def criar_novo_produto(self, cod_empresa: int, produto_data: CriarNovoProdutoRequest) -> CriarNovoProdutoResponse:
        empresa = self.emp_repo.get_empresa_by_id(cod_empresa)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")

        if self.produto_repo.buscar_por_cod_barras(produto_data.cod_barras):
            raise ValueError("Produto já existe.")

        produto = ProdutoDeliveryModel(
            cod_barras=produto_data.cod_barras,
            descricao=produto_data.descricao,
            cod_categoria=produto_data.cod_categoria,
            imagem=produto_data.imagem,
            data_cadastro=produto_data.data_cadastro or datetime.utcnow(),
        )

        empresas = [cod_empresa]

        produto.produtos_empresa = [
            ProdutoEmpDeliveryModel(
                empresa_id=int(emp),
                cod_barras=produto.cod_barras,
                preco_venda=produto_data.preco_venda,
                custo=produto_data.custo or 0,
                vitrine_id=produto_data.vitrine_id,
                produto=produto
            ) for emp in empresas
        ]

        produto = self.produto_repo.criar_novo_produto(produto)
        return CriarNovoProdutoResponse.model_validate(produto, from_attributes=True)


    def atualizar_produto(self, cod_barras: str, data: CriarNovoProdutoRequest) -> CriarNovoProdutoResponse:
        # valida existência
        if not self.produto_repo.buscar_por_cod_barras(cod_barras):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")

        # monta dict de atualização
        update_data = {
            "descricao": data.descricao,
            "cod_categoria": data.cod_categoria,
            "imagem": data.imagem,
            "data_cadastro": data.data_cadastro or datetime.utcnow(),
            "preco_venda": data.preco_venda,
            "custo": data.custo or 0,
            "vitrine_id": data.vitrine_id,
        }

        prod = self.produto_repo.update_produto(cod_barras, update_data)
        return CriarNovoProdutoResponse.model_validate(prod, from_attributes=True)

    def deletar_produto(self, cod_barras: str) -> bool:
        deleted = self.produto_repo.delete_produto(cod_barras)
        return deleted
