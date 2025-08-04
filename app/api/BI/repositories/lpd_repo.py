# app/api/BI/repositories/lpd_repo.py
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.public.models.categoriaprod_public_model import CategoriaProdutoPublicModel
from app.api.public.models.lpd_model import get_lpd_model


class LpdRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_vendas_por_departamento(self, ano_mes: str, subempresas: list[int]):
        """
        Retorna total de vendas por departamento (sem separar por empresa)
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
                CategoriaProdutoPublicModel.cate_codsubempresa.in_(subempresas),
                Lpd.lcpd_situacao == "N",
                Lpd.lcpd_tipoprocesso == "VN"
            )
            .group_by(CategoriaProdutoPublicModel.cate_codsubempresa)
            .order_by(func.sum(Lpd.lcpd_valor).desc())
        )

        return self.db.execute(stmt).all()

    def get_vendas_por_empresa_e_departamento(self, ano_mes: str, subempresas: list[int]):
        """
        Retorna total de vendas por empresa e por departamento
        """
        Lpd = get_lpd_model(ano_mes)

        stmt = (
            select(
                Lpd.lcpd_empresa.label("empresa"),
                CategoriaProdutoPublicModel.cate_codsubempresa.label("departamento"),
                func.sum(Lpd.lcpd_valor).label("total_vendas")
            )
            .join(
                CategoriaProdutoPublicModel,
                CategoriaProdutoPublicModel.cate_codigo == Lpd.lcpd_codcategoria
            )
            .where(
                CategoriaProdutoPublicModel.cate_codsubempresa.in_(subempresas),
                Lpd.lcpd_situacao == "N",
                Lpd.lcpd_tipoprocesso == "VN"
            )
            .group_by(Lpd.lcpd_empresa, CategoriaProdutoPublicModel.cate_codsubempresa)
            .order_by(func.sum(Lpd.lcpd_valor).desc())
        )

        return self.db.execute(stmt).all()
