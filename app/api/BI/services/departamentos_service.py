from sqlalchemy.orm import Session
from app.api.BI.repositories.lpd_repo import LpdRepository
from app.api.BI.repositories.subempresas_repo import SubEmpresasPublicRepository
from app.api.BI.schemas.departamento_schema import VendasPorDepartamento


class DepartamentosPublicService:
    def __init__(self, db: Session):
        self.db = db
        self.repo_subempresas = SubEmpresasPublicRepository(db)
        self.repo_lpd = LpdRepository(db)

    def get_mais_vendidos(self, ano_mes: str) -> list[VendasPorDepartamento]:
        # 1. Subempresas que vendem
        subempresas = self.repo_subempresas.get_all_isvendas()
        codigos_subempresas = [s.sube_codigo for s in subempresas if s.sube_codigo is not None]

        if not codigos_subempresas:
            return []

        # 2. Resultados agregados por cod_subempresa
        vendas_por_departamento = self.repo_lpd.get_vendas_por_departamento(ano_mes, codigos_subempresas)

        # 3. Mapeia código → nome para facilitar match
        mapa_cod_nome = {
            s.sube_codigo: s.sube_descricao for s in subempresas
        }

        # 4. Monta lista com nome
        return [
            VendasPorDepartamento(
                departamento=mapa_cod_nome.get(dep),
                total_vendas=total
            )
            for dep, total in vendas_por_departamento
            if dep in mapa_cod_nome
        ]
