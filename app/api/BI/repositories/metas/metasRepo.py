from typing import List

from sqlalchemy import select, text
from datetime import date

from app.api.BI.models.meta_model import Meta
from app.api.BI.schemas.metas_types import TypeConsultaMetaRequest, TypeTotaisPorEmpresaMetaResponse


def buscar_meta(session, empresa: str, data: date, tipo: str) -> Meta | None:
    return session.execute(
        select(Meta).where(
            Meta.mefi_codempresa == empresa,
            Meta.mefi_data == data,
            Meta.mefi_descricao == tipo,
        )
    ).scalar_one_or_none()

def inserir_meta(session, meta: Meta):
    session.add(meta)

def atualizar_valor_meta(meta: Meta, novo_valor: float):
    meta.mefi_valor = novo_valor



def buscar_metas_por_periodo(session, request: TypeConsultaMetaRequest) -> List[TypeTotaisPorEmpresaMetaResponse]:
    empresas = ','.join(f"'{e}'" for e in request.empresas)
    data_inicio = request.dataInicio
    data_final = request.dataFinal or request.dataInicio

    query = f"""
        SELECT 
            mefi_codempresa AS codempresa,
            mefi_descricao AS tipo,
            SUM(mefi_valor) AS valormeta
        FROM mensura.metas
        WHERE mefi_data BETWEEN '{data_inicio}' AND '{data_final}'
        AND mefi_codempresa IN ({empresas})
        GROUP BY mefi_codempresa, mefi_descricao
    """

    result = session.execute(text(query))
    dados = result.fetchall()

    return [
        TypeTotaisPorEmpresaMetaResponse(
            codempresa=row[0],
            tipo=row[1],
            valorMeta=float(row[2])
        )
        for row in dados
    ]

