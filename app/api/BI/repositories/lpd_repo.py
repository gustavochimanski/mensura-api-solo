from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.api.public.models.categoriaprod_public_model import CategoriaProdutoPublicModel
from app.api.public.models.lpd_model import get_lpd_model


class LpdRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_vendas_por_departamento(self, ano_mes: str, subempresas: list[int]):
        """
        Retorna total de vendas por departamento (sem separar por empresa).
        Agrupa por cate_codsubempresa, somando apenas quando lcpd_subempresa == cate_codsubempresa.
        """
        Lpd = get_lpd_model(ano_mes)

        stmt = (
            select(
                CategoriaProdutoPublicModel.cate_codsubempresa.label("departamento"),
                func.sum(Lpd.lcpd_valor).label("total_vendas")
            )
            .join(
                CategoriaProdutoPublicModel,
                CategoriaProdutoPublicModel.cate_codigo == Lpd.lcpd_codcategoria
            )
            .where(
                # filtra só categorias válidas
                CategoriaProdutoPublicModel.cate_codsubempresa.in_(subempresas),
                # exige que o lançamento seja daquela mesma subempresa
                Lpd.lcpd_subempresa == CategoriaProdutoPublicModel.cate_codsubempresa,
                Lpd.lcpd_situacao == "N",
                Lpd.lcpd_tipoprocesso == "VN"
            )
            .group_by(CategoriaProdutoPublicModel.cate_codsubempresa)
            .order_by(func.sum(Lpd.lcpd_valor).desc())
        )

        return self.db.execute(stmt).all()

    def get_vendas_por_empresa_e_departamento(self, ano_mes: str, subempresas: list[int]):
        """
        Retorna, para cada empresa e cada departamento, o total de vendas.
        - empresa: lcpd_codempresa (ex: '001', '002')
        - departamento: cate_codsubempresa (ex: 121000, 122001)
        Somando apenas quando lcpd_subempresa == cate_codsubempresa.
        """
        Lpd = get_lpd_model(ano_mes)

        stmt = (
            select(
                Lpd.lcpd_codempresa.label("empresa"),
                CategoriaProdutoPublicModel.cate_codsubempresa.label("departamento"),
                func.sum(Lpd.lcpd_valor).label("total_vendas")
            )
            .join(
                CategoriaProdutoPublicModel,
                CategoriaProdutoPublicModel.cate_codigo == Lpd.lcpd_codcategoria
            )
            .where(
                # categorias válidas
                CategoriaProdutoPublicModel.cate_codsubempresa.in_(subempresas),
                # só soma se a subempresa do lançamento for a mesma da categoria
                Lpd.lcpd_subempresa == CategoriaProdutoPublicModel.cate_codsubempresa,
                Lpd.lcpd_situacao == "N",
                Lpd.lcpd_tipoprocesso == "VN"
            )
            .group_by(
                Lpd.lcpd_codempresa,
                CategoriaProdutoPublicModel.cate_codsubempresa
            )
            .order_by(func.sum(Lpd.lcpd_valor).desc())
        )

        return self.db.execute(stmt).all()
