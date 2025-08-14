from sqlalchemy.orm import Session


class ProdutosMensuraService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProdutoRepository(db)

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