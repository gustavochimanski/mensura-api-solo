from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.public.models.categoriaprod_public_model import CategoriaProdutoPublicModel
from app.api.public.models.lpd_model import get_lpd_model


class LpdRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_vendas_por_departamento_periodo(self, subempresas: list[int], dt_inicio, dt_fim):
        Lpd = get_lpd_model(dt_inicio.strftime("%Y%m"))

        stmt = (
            select(
                CategoriaProdutoPublicModel.cate_codsubempresa.label("departamento"),
                func.sum(Lpd.lcpd_valor).label("total_vendas"),
            )
            .join(
                CategoriaProdutoPublicModel,
                CategoriaProdutoPublicModel.cate_codigo == Lpd.lcpd_codcategoria
            )
            .where(
                CategoriaProdutoPublicModel.cate_codsubempresa.in_(subempresas),
                Lpd.lcpd_situacao == "N",
                Lpd.lcpd_tipoprocesso == "VN",
                Lpd.lcpd_dtmvto.between(dt_inicio, dt_fim),
            )
            .group_by(CategoriaProdutoPublicModel.cate_codsubempresa)
            .order_by(func.sum(Lpd.lcpd_valor).desc())
        )

        return self.db.execute(stmt).all()

    def get_vendas_por_empresa_e_departamento_periodo(self, subempresas: list[int], dt_inicio, dt_fim):
        Lpd = get_lpd_model(dt_inicio.strftime("%Y%m"))

        stmt = (
            select(
                Lpd.lcpd_codempresa.label("empresa"),
                CategoriaProdutoPublicModel.cate_codsubempresa.label("departamento"),
                func.sum(Lpd.lcpd_valor).label("total_vendas"),
            )
            .join(
                CategoriaProdutoPublicModel,
                CategoriaProdutoPublicModel.cate_codigo == Lpd.lcpd_codcategoria
            )
            .where(
                CategoriaProdutoPublicModel.cate_codsubempresa.in_(subempresas),
                Lpd.lcpd_situacao == "N",
                Lpd.lcpd_tipoprocesso == "VN",
                Lpd.lcpd_dtmvto.between(dt_inicio, dt_fim),
            )
            .group_by(
                Lpd.lcpd_codempresa,
                CategoriaProdutoPublicModel.cate_codsubempresa
            )
            .order_by(func.sum(Lpd.lcpd_valor).desc())
        )

        return self.db.execute(stmt).all()
