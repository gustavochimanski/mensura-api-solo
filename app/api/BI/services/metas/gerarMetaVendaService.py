import logging
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session

from app.api.BI.models.meta_model import Meta
from app.api.BI.repositories.vendas.vendaByDay import buscar_vendas_dia
from app.api.BI.schemas.metas_types import MetasEmpresa, MetaDiaria
from app.api.BI.repositories.metas.metasRepo import (
    buscar_meta,
    inserir_meta,
    atualizar_valor_meta,
)


logger = logging.getLogger(__name__)
NOME_REQUISICAO = "[POST /metas/gerar-venda]"

def filtrar_outliers(vendas: List[float], divisor: float = 2) -> List[float]:
    if not vendas:
        return []
    max_valor = max(vendas)
    if max_valor == 0:
        return vendas
    filtradas = [v for v in vendas if v >= max_valor / divisor]
    removidos = len(vendas) - len(filtradas)
    if removidos > 0:
        logger.warning(f"{NOME_REQUISICAO} ⚠️ {removidos} valores removidos (outliers): {filtradas}")
    return filtradas

def gerarMetaVendaService(
    session: Session,
    dataInicial: str,
    dataFinal: str,
    empresas: List[str],
    fator_crescimento: float = 0.8  #
) -> List[MetasEmpresa]:
    inicio = datetime.strptime(dataInicial, "%Y-%m-%d").date()
    fim = datetime.strptime(dataFinal, "%Y-%m-%d").date()
    dias_total = (fim - inicio).days + 1

    tipo_meta = "metaVenda"
    resultado: List[MetasEmpresa] = []

    try:
        for empresa in empresas:
            metas_dia: List[MetaDiaria] = []
            metas_valores: List[float] = []

            for i in range(dias_total):
                dia = inicio + timedelta(days=i)
                vendas_anteriores = buscar_vendas_dia(session, empresa, dia)
                logger.info(f"{NOME_REQUISICAO} Empresa: {empresa} | Dia: {dia} | Vendas brutas: {vendas_anteriores}")

                if not vendas_anteriores or all(v == 0 for v in vendas_anteriores):
                    logger.warning(f"{NOME_REQUISICAO} ⚠️ Sem histórico válido para {empresa} em {dia}")
                    continue

                vendas_filtradas = filtrar_outliers(vendas_anteriores)
                if not vendas_filtradas:
                    logger.warning(f"{NOME_REQUISICAO} ❌ Todos os valores foram descartados para {empresa} em {dia}")
                    continue

                media = sum(vendas_filtradas) / len(vendas_filtradas)
                fator = ((vendas_filtradas[0] - media) / vendas_filtradas[0]) if vendas_filtradas[0] > 0 else 0
                meta_valor_base = media * (1 + fator)

                # 👇 Aplica o fator de crescimento aqui
                meta_valor_final = round(meta_valor_base * (1 + fator_crescimento), 2)

                logger.info(
                    f"{NOME_REQUISICAO} 🎯 Base: {meta_valor_base:.2f} | Crescimento aplicado: {fator_crescimento:.2%} | Final: R${meta_valor_final:.2f}"
                )

                meta_existente = buscar_meta(session, empresa, dia, tipo_meta)
                if meta_existente:
                    atualizar_valor_meta(meta_existente, meta_valor_final)
                    logger.info(f"{NOME_REQUISICAO} 🔄 Meta atualizada para {empresa} em {dia}: R${meta_valor_final}")
                else:
                    nova_meta = Meta(
                        mefi_codempresa=empresa,
                        mefi_data=dia,
                        mefi_valor=meta_valor_final,
                        mefi_descricao=tipo_meta,
                    )
                    inserir_meta(session, nova_meta)
                    logger.info(f"{NOME_REQUISICAO} 🆕 Nova meta criada para {empresa} em {dia}: R${meta_valor_final}")

                metas_dia.append(MetaDiaria(
                    data=dia.strftime("%Y-%m-%d"),
                    meta_gerada=meta_valor_final
                ))
                metas_valores.append(meta_valor_final)

            resultado.append(MetasEmpresa(
                empresa=empresa,
                metas=metas_dia
            ))

        session.commit()
        return resultado

    except Exception as e:
        session.rollback()
        logger.error(f"{NOME_REQUISICAO} ❌ Erro ao gerar metas: {e}")
        raise Exception(f"Erro ao gerar metas: {e}")
