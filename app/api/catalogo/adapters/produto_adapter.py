from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from app.api.catalogo.contracts.produto_contract import (
    IProdutoContract,
    ProdutoDTO,
    ProdutoEmpDTO,
)
from app.api.catalogo.repositories.repo_produto import ProdutoMensuraRepository
from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel


class ProdutoAdapter(IProdutoContract):
    """Implementação do contrato de produtos baseada nos repositórios atuais."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ProdutoMensuraRepository(db)

    def _to_produto_dto(self, produto: ProdutoModel) -> ProdutoDTO:
        return ProdutoDTO(
            cod_barras=produto.cod_barras,
            descricao=produto.descricao,
            ativo=bool(getattr(produto, "ativo", True)),
            imagem=getattr(produto, "imagem", None),
            unidade_medida=getattr(produto, "unidade_medida", None),
        )

    def _to_produto_emp_dto(self, pe: ProdutoEmpModel, include_produto: bool = True) -> ProdutoEmpDTO:
        return ProdutoEmpDTO(
            empresa_id=pe.empresa_id,
            cod_barras=pe.cod_barras,
            preco_venda=pe.preco_venda,
            disponivel=bool(pe.disponivel),
            exibir_delivery=bool(pe.exibir_delivery),
            produto=self._to_produto_dto(pe.produto) if include_produto and pe.produto else None,
        )

    def obter_produto_emp_por_cod(self, empresa_id: int, cod_barras: str) -> Optional[ProdutoEmpDTO]:
        pe = (
            self.db.query(ProdutoEmpModel)
            .options(joinedload(ProdutoEmpModel.produto))
            .filter(ProdutoEmpModel.empresa_id == empresa_id, ProdutoEmpModel.cod_barras == cod_barras)
            .first()
        )
        if not pe:
            return None
        return self._to_produto_emp_dto(pe, include_produto=True)

    def validar_produto_disponivel(self, empresa_id: int, cod_barras: str, quantidade: int = 1) -> bool:
        pe = self.repo.get_produto_emp(empresa_id, cod_barras)
        if not pe or not pe.disponivel:
            return False
        # Atualmente não há controle de estoque no modelo; valida flags básicas
        if pe.produto and hasattr(pe.produto, "ativo") and not bool(pe.produto.ativo):
            return False
        return True

    def listar_produtos_ativos_da_empresa(self, empresa_id: int, apenas_delivery: bool = True) -> List[ProdutoDTO]:
        produtos = self.repo.buscar_produtos_da_empresa(
            empresa_id=empresa_id,
            offset=0,
            limit=500,
            apenas_disponiveis=True,
            apenas_delivery=apenas_delivery,
        )
        return [self._to_produto_dto(p) for p in produtos]

