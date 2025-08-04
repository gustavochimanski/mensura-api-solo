# app/api/BI/services/departamentos_service.py
from collections import defaultdict
from sqlalchemy.orm import Session

from app.api.BI.repositories.lpd_repo import LpdRepository
from app.api.BI.repositories.subempresas_repo import SubEmpresasPublicRepository
from app.api.BI.schemas.departamento_schema import (
    VendasPorDepartamento,
    VendasPorEmpresaComDepartamentos,
)
from app.api.public.models.categoriaprod_public_model import CategoriaProdutoPublicModel
from app.utils.logger import logger


class DepartamentosPublicService:
    def __init__(self, db: Session):
        self.db = db
        self.repo_subempresas = SubEmpresasPublicRepository(db)
        self.repo_lpd = LpdRepository(db)

    def get_mais_vendidos_geral(self, ano_mes: str) -> list[VendasPorDepartamento]:
        """
        Retorna total de vendas por departamento (geral, sem separar por empresa)
        """
        subempresas = self.repo_subempresas.get_all_isvendas()
        codigos_subempresas = [s.sube_codigo for s in subempresas if s.sube_codigo is not None]
        if not codigos_subempresas:
            return []

        vendas_por_departamento = self.repo_lpd.get_vendas_por_departamento(ano_mes, codigos_subempresas)
        # Usa código como “nome” temporariamente (ou monte mapa de nomes igual abaixo)
        return [
            VendasPorDepartamento(
                departamento=str(dep),
                total_vendas=float(total)
            )
            for dep, total in vendas_por_departamento
        ]

    def get_mais_vendidos(self, ano_mes: str) -> list[VendasPorEmpresaComDepartamentos]:
        """
        Retorna total de vendas por empresa e por departamento,
        já trazendo os nomes corretos tanto de empresa quanto de departamento.
        """
        subempresas = self.repo_subempresas.get_all_isvendas()
        codigos_subempresas = [s.sube_codigo for s in subempresas if s.sube_codigo is not None]
        if not codigos_subempresas:
            return []

        # 1) Busca vendas “cruas”
        vendas = self.repo_lpd.get_vendas_por_empresa_e_departamento(ano_mes, codigos_subempresas)

        # 2) Mapeia código → nome das empresas
        mapa_empresas = {s.sube_codigo: s.sube_descricao for s in subempresas}

        # 3) Mapeia código → nome dos departamentos
        departamentos = (
            self.db
            .query(
                CategoriaProdutoPublicModel.cate_codsubempresa,
                CategoriaProdutoPublicModel.cate_descricao
            )
            .filter(CategoriaProdutoPublicModel.cate_codsubempresa.in_(codigos_subempresas))
            .distinct()
            .all()
        )
        mapa_departamentos = {cod: desc for cod, desc in departamentos}

        # 4) Agrupa por empresa
        agrupado: dict[str, list[VendasPorDepartamento]] = defaultdict(list)
        for cod_empresa, cod_dep, total in vendas:
            nome_emp = mapa_empresas.get(cod_empresa)
            nome_dep = mapa_departamentos.get(cod_dep)
            if nome_emp and nome_dep:
                agrupado[nome_emp].append(
                    VendasPorDepartamento(
                        departamento=nome_dep,
                        total_vendas=float(total)
                    )
                )

        # 5) Monta lista final
        return [
            VendasPorEmpresaComDepartamentos(
                empresa=empresa,
                departamentos=deps
            )
            for empresa, deps in agrupado.items()
        ]
