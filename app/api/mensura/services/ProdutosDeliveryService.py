# services/produtos_service.py
from datetime import datetime

from sqlalchemy.orm import Session

from app.api.mensura.repositories.delivery.produtosDeliveryRepository import ProdutoDeliveryRepository
from app.api.mensura.schemas.delivery.produtos.produtosDelivery_schema import ProdutoListItem, CriarNovoProdutoResponse, \
    CriarNovoProdutoRequest
from app.api.mensura.models.cad_prod_delivery_model import ProdutoDeliveryModel
from app.api.mensura.models.cad_prod_emp_delivery_model import ProdutosEmpDeliveryModel
from app.api.public.repositories.empresas.consultaEmpresas import EmpresasRepository
from app.utils.logger import logger


class ProdutosDeliveryService:
    def __init__(self, db: Session):
        self.db = db
        self.produto_repo = ProdutoDeliveryRepository(db)

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

    def criar_novo_produto(self, produto_data: CriarNovoProdutoRequest) -> CriarNovoProdutoResponse:
        if self.produto_repo.buscar_por_cod_barras(produto_data.cod_barras):
            raise ValueError("Produto já existe.")

        produto = ProdutoDeliveryModel(
            cod_barras=produto_data.cod_barras,
            descricao=produto_data.descricao,
            cod_categoria=produto_data.cod_categoria,
            imagem=produto_data.imagem,
            data_cadastro=produto_data.data_cadastro or datetime.utcnow(),
        )

        # empresas = EmpresasRepository(self.db).buscar_codigos_ativos()
        empresas = [1]
        logger.info(f"Empresas: {empresas}")
        produto.produtos_empresa = [
            ProdutosEmpDeliveryModel(
                empresa=int(emp),
                cod_barras=produto.cod_barras,
                preco_venda=produto_data.preco_venda,
                custo=produto_data.custo or 0,
                subcategoria_id=produto_data.subcategoria_id,
                produto=produto
            ) for emp in empresas
        ]

        produto = self.produto_repo.criar_novo_produto(produto)
        return CriarNovoProdutoResponse.model_validate(produto, from_attributes=True)
