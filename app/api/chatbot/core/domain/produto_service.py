"""
Domain Service de Produtos.

Responsável por busca e resolução de produtos/receitas/combos no banco,
incluindo heurísticas (sinônimos, correção de digitação, etc).
"""

from __future__ import annotations

import re
from difflib import get_close_matches
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


class ProdutoDomainService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id

    def buscar_produtos(self, termo_busca: str = "") -> List[Dict[str, Any]]:
        """Busca produtos no banco de dados usando SQL direto."""
        try:
            if termo_busca:
                query = text(
                    """
                    SELECT p.cod_barras, p.descricao, pe.preco_venda
                    FROM catalogo.produtos p
                    JOIN catalogo.produtos_empresa pe ON p.cod_barras = pe.cod_barras
                    WHERE pe.empresa_id = :empresa_id
                    AND p.ativo = true
                    AND pe.disponivel = true
                    AND p.descricao ILIKE :termo
                    ORDER BY p.descricao
                    LIMIT 10
                    """
                )
                result = self.db.execute(
                    query, {"empresa_id": self.empresa_id, "termo": f"%{termo_busca}%"}
                )
            else:
                query = text(
                    """
                    SELECT p.cod_barras, p.descricao, pe.preco_venda
                    FROM catalogo.produtos p
                    JOIN catalogo.produtos_empresa pe ON p.cod_barras = pe.cod_barras
                    WHERE pe.empresa_id = :empresa_id
                    AND p.ativo = true
                    AND pe.disponivel = true
                    ORDER BY p.descricao
                    LIMIT 10
                    """
                )
                result = self.db.execute(query, {"empresa_id": self.empresa_id})

            return [
                {"id": row[0], "nome": row[1], "preco": float(row[2])}
                for row in result.fetchall()
            ]
        except Exception as e:
            print(f"Erro ao buscar produtos: {e}")
            return []

    def buscar_promocoes(self) -> List[Dict[str, Any]]:
        """Busca produtos em promoção/destaque usando SQL direto (prioriza receitas)."""
        try:
            produtos: List[Dict[str, Any]] = []

            # Primeiro busca receitas (pizzas, lanches) - são os destaques
            query_receitas = text(
                """
                SELECT id, nome, preco_venda
                FROM catalogo.receitas
                WHERE empresa_id = :empresa_id
                AND ativo = true
                AND disponivel = true
                ORDER BY nome
                LIMIT 3
                """
            )
            result_receitas = self.db.execute(query_receitas, {"empresa_id": self.empresa_id})

            for row in result_receitas.fetchall():
                produtos.append(
                    {
                        "id": f"receita_{row[0]}",
                        "nome": row[1],
                        "preco": float(row[2]) if row[2] else 0.0,
                    }
                )

            # Se não tiver receitas suficientes, busca produtos
            if len(produtos) < 3:
                query_produtos = text(
                    """
                    SELECT p.cod_barras, p.descricao, pe.preco_venda
                    FROM catalogo.produtos p
                    JOIN catalogo.produtos_empresa pe ON p.cod_barras = pe.cod_barras
                    WHERE pe.empresa_id = :empresa_id
                    AND p.ativo = true
                    AND pe.disponivel = true
                    ORDER BY p.descricao
                    LIMIT :limit
                    """
                )
                result_produtos = self.db.execute(
                    query_produtos,
                    {"empresa_id": self.empresa_id, "limit": 5 - len(produtos)},
                )

                for row in result_produtos.fetchall():
                    produtos.append({"id": row[0], "nome": row[1], "preco": float(row[2])})

            return produtos[:5]
        except Exception as e:
            print(f"Erro ao buscar promoções: {e}")
            return []

    def buscar_todos_produtos(self) -> List[Dict[str, Any]]:
        """Busca TODOS os produtos disponíveis no banco (produtos + receitas)."""
        try:
            produtos: List[Dict[str, Any]] = []

            # 1. Produtos simples (bebidas, etc)
            query_produtos = text(
                """
                SELECT p.cod_barras, p.descricao, pe.preco_venda
                FROM catalogo.produtos p
                JOIN catalogo.produtos_empresa pe ON p.cod_barras = pe.cod_barras
                WHERE pe.empresa_id = :empresa_id
                AND p.ativo = true
                AND pe.disponivel = true
                ORDER BY p.descricao
                """
            )
            result_produtos = self.db.execute(query_produtos, {"empresa_id": self.empresa_id})
            for row in result_produtos.fetchall():
                produtos.append(
                    {
                        "id": row[0],
                        "nome": row[1],
                        "descricao": "",
                        "preco": float(row[2]),
                        "tipo": "produto",
                    }
                )

            # 2. Receitas (pizzas, lanches, etc)
            query_receitas = text(
                """
                SELECT id, nome, preco_venda, descricao
                FROM catalogo.receitas
                WHERE empresa_id = :empresa_id
                AND ativo = true
                AND disponivel = true
                ORDER BY nome
                """
            )
            result_receitas = self.db.execute(query_receitas, {"empresa_id": self.empresa_id})
            for row in result_receitas.fetchall():
                produtos.append(
                    {
                        "id": f"receita_{row[0]}",
                        "nome": row[1],
                        "preco": float(row[2]) if row[2] else 0.0,
                        "descricao": row[3],
                        "tipo": "receita",
                    }
                )

            return produtos
        except Exception as e:
            print(f"Erro ao buscar todos produtos: {e}")
            import traceback

            traceback.print_exc()
            return []

    def normalizar_termo_busca(self, termo: str) -> str:
        """
        Normaliza termo de busca removendo acentos, espaços extras e caracteres especiais.
        """

        def remover_acentos(texto: str) -> str:
            acentos = {
                "á": "a",
                "à": "a",
                "ã": "a",
                "â": "a",
                "ä": "a",
                "é": "e",
                "ê": "e",
                "ë": "e",
                "í": "i",
                "î": "i",
                "ï": "i",
                "ó": "o",
                "ô": "o",
                "õ": "o",
                "ö": "o",
                "ú": "u",
                "û": "u",
                "ü": "u",
                "ç": "c",
                "ñ": "n",
            }
            for acentuado, sem_acento in acentos.items():
                texto = texto.replace(acentuado, sem_acento)
                texto = texto.replace(acentuado.upper(), sem_acento.upper())
            return texto

        termo_normalizado = remover_acentos((termo or "").lower().strip())
        termo_normalizado = re.sub(r"[^\w\s]", "", termo_normalizado)
        termo_normalizado = re.sub(r"\s+", " ", termo_normalizado).strip()
        return termo_normalizado

    def corrigir_termo_busca(self, termo: str, lista_referencia: List[str], threshold: float = 0.6) -> str:
        """
        Corrige erros de digitação usando difflib.
        Exemplo: "te hmburg" -> "hamburg"
        """
        if not termo or not lista_referencia:
            return termo

        termo_normalizado = self.normalizar_termo_busca(termo)
        matches = get_close_matches(
            termo_normalizado,
            [self.normalizar_termo_busca(ref) for ref in lista_referencia],
            n=1,
            cutoff=threshold,
        )

        if matches:
            for ref in lista_referencia:
                if self.normalizar_termo_busca(ref) == matches[0]:
                    print(f"🔧 Correção: '{termo}' -> '{ref}'")
                    return ref

        return termo

    def expandir_sinonimos(self, termo: str) -> List[str]:
        """
        Expande termo com sinônimos e variações comuns.
        Exemplo: "hamburg" -> ["hamburg", "hamburger", "burger", "hamburguer"]
        """
        sinonimos = {
            "hamburg": ["hamburger", "burger", "hamburguer", "hambúrguer"],
            "burger": ["hamburger", "hamburg", "hamburguer", "hambúrguer"],
            "hamburger": ["hamburg", "burger", "hamburguer", "hambúrguer"],
            "pizza": ["pizzas"],
            "refri": ["refrigerante", "refris"],
            "refrigerante": ["refri", "refris"],
            "coca": ["coca cola", "cocacola"],
            "batata": ["batatas", "fritas"],
            "batata frita": ["batatas fritas", "fritas"],
            "x": ["x-", "xis"],
            "xis": ["x-", "x"],
        }

        termo_lower = (termo or "").lower().strip()
        termos_expandidos: List[str] = [termo]

        for chave, valores in sinonimos.items():
            if chave in termo_lower:
                termos_expandidos.extend(valores)
                for valor in valores:
                    termo_substituido = termo_lower.replace(chave, valor)
                    if termo_substituido != termo_lower:
                        termos_expandidos.append(termo_substituido)

        termos_unicos: List[str] = []
        for t in termos_expandidos:
            if t not in termos_unicos:
                termos_unicos.append(t)

        return termos_unicos[:5]

    def buscar_produtos_inteligente(self, termo_busca: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Busca inteligente em produtos, receitas e combos com:
        - Correção de erros de digitação
        - Suporte a variações (burger/hamburg)
        - Busca rápida e otimizada
        - Limitada para escalabilidade
        """
        if not termo_busca or len(termo_busca.strip()) < 2:
            return []

        try:
            termo_original = termo_busca.strip()
            termo_normalizado = self.normalizar_termo_busca(termo_original)

            termos_busca = self.expandir_sinonimos(termo_original)
            termos_busca.append(termo_normalizado)
            termos_busca = list(dict.fromkeys(termos_busca))[:3]

            resultados: List[Dict[str, Any]] = []

            # Produtos
            for termo in termos_busca:
                termo_sql = f"%{termo}%"
                query_produtos = text(
                    """
                    SELECT p.cod_barras, p.descricao, pe.preco_venda, 'produto' as tipo
                    FROM catalogo.produtos p
                    JOIN catalogo.produtos_empresa pe ON p.cod_barras = pe.cod_barras
                    WHERE pe.empresa_id = :empresa_id
                    AND p.ativo = true
                    AND pe.disponivel = true
                    AND (
                        LOWER(REPLACE(REPLACE(p.descricao, '-', ''), ' ', '')) LIKE LOWER(REPLACE(REPLACE(:termo, '-', ''), ' ', ''))
                        OR LOWER(p.descricao) LIKE LOWER(:termo)
                    )
                    ORDER BY
                        CASE
                            WHEN LOWER(p.descricao) = LOWER(:termo_exato) THEN 1
                            WHEN LOWER(p.descricao) LIKE LOWER(:termo_inicio) THEN 2
                            ELSE 3
                        END,
                        p.descricao
                    LIMIT :limit
                    """
                )
                result = self.db.execute(
                    query_produtos,
                    {
                        "empresa_id": self.empresa_id,
                        "termo": termo_sql,
                        "termo_exato": termo,
                        "termo_inicio": f"{termo}%",
                        "limit": limit,
                    },
                )
                for row in result.fetchall():
                    produto = {"id": row[0], "nome": row[1], "preco": float(row[2]), "tipo": row[3]}
                    if not any(r.get("id") == produto["id"] and r.get("tipo") == produto["tipo"] for r in resultados):
                        resultados.append(produto)
                if len(resultados) >= limit:
                    break

            # Receitas
            if len(resultados) < limit:
                for termo in termos_busca:
                    termo_sql = f"%{termo}%"
                    query_receitas = text(
                        """
                        SELECT id, nome, preco_venda, 'receita' as tipo
                        FROM catalogo.receitas
                        WHERE empresa_id = :empresa_id
                        AND ativo = true
                        AND disponivel = true
                        AND (
                            LOWER(REPLACE(REPLACE(nome, '-', ''), ' ', '')) LIKE LOWER(REPLACE(REPLACE(:termo, '-', ''), ' ', ''))
                            OR LOWER(nome) LIKE LOWER(:termo)
                            OR (descricao IS NOT NULL AND LOWER(descricao) LIKE LOWER(:termo))
                        )
                        ORDER BY
                            CASE
                                WHEN LOWER(nome) = LOWER(:termo_exato) THEN 1
                                WHEN LOWER(nome) LIKE LOWER(:termo_inicio) THEN 2
                                ELSE 3
                            END,
                            nome
                        LIMIT :limit
                        """
                    )
                    result = self.db.execute(
                        query_receitas,
                        {
                            "empresa_id": self.empresa_id,
                            "termo": termo_sql,
                            "termo_exato": termo,
                            "termo_inicio": f"{termo}%",
                            "limit": limit - len(resultados),
                        },
                    )
                    for row in result.fetchall():
                        receita = {
                            "id": f"receita_{row[0]}",
                            "nome": row[1],
                            "preco": float(row[2]) if row[2] else 0.0,
                            "tipo": row[3],
                        }
                        if not any(r.get("id") == receita["id"] and r.get("tipo") == receita["tipo"] for r in resultados):
                            resultados.append(receita)
                    if len(resultados) >= limit:
                        break

            # Combos
            if len(resultados) < limit:
                for termo in termos_busca:
                    termo_sql = f"%{termo}%"
                    query_combos = text(
                        """
                        SELECT id, titulo, preco_total, 'combo' as tipo
                        FROM catalogo.combos
                        WHERE empresa_id = :empresa_id
                        AND ativo = true
                        AND (
                            (titulo IS NOT NULL AND (
                                LOWER(REPLACE(REPLACE(titulo, '-', ''), ' ', '')) LIKE LOWER(REPLACE(REPLACE(:termo, '-', ''), ' ', ''))
                                OR LOWER(titulo) LIKE LOWER(:termo)
                            ))
                            OR LOWER(descricao) LIKE LOWER(:termo)
                        )
                        ORDER BY
                            CASE
                                WHEN titulo IS NOT NULL AND LOWER(titulo) = LOWER(:termo_exato) THEN 1
                                WHEN titulo IS NOT NULL AND LOWER(titulo) LIKE LOWER(:termo_inicio) THEN 2
                                ELSE 3
                            END,
                            titulo
                        LIMIT :limit
                        """
                    )
                    result = self.db.execute(
                        query_combos,
                        {
                            "empresa_id": self.empresa_id,
                            "termo": termo_sql,
                            "termo_exato": termo,
                            "termo_inicio": f"{termo}%",
                            "limit": limit - len(resultados),
                        },
                    )
                    for row in result.fetchall():
                        combo = {
                            "id": f"combo_{row[0]}",
                            "nome": row[1] or f"Combo {row[0]}",
                            "preco": float(row[2]) if row[2] else 0.0,
                            "tipo": row[3],
                        }
                        if not any(r.get("id") == combo["id"] and r.get("tipo") == combo["tipo"] for r in resultados):
                            resultados.append(combo)
                    if len(resultados) >= limit:
                        break

            # Fallback: correção por lista de referência
            if not resultados:
                query_referencia = text(
                    """
                    (
                        SELECT descricao as nome FROM catalogo.produtos p
                        JOIN catalogo.produtos_empresa pe ON p.cod_barras = pe.cod_barras
                        WHERE pe.empresa_id = :empresa_id AND p.ativo = true AND pe.disponivel = true
                        LIMIT 50
                    )
                    UNION
                    (
                        SELECT nome FROM catalogo.receitas
                        WHERE empresa_id = :empresa_id AND ativo = true AND disponivel = true
                        LIMIT 30
                    )
                    UNION
                    (
                        SELECT COALESCE(titulo, descricao) as nome FROM catalogo.combos
                        WHERE empresa_id = :empresa_id AND ativo = true
                        LIMIT 20
                    )
                    """
                )
                result_ref = self.db.execute(query_referencia, {"empresa_id": self.empresa_id})
                lista_referencia = [row[0] for row in result_ref.fetchall()]
                termo_corrigido = self.corrigir_termo_busca(termo_original, lista_referencia)
                if termo_corrigido != termo_original:
                    return self.buscar_produtos_inteligente(termo_corrigido, limit)

            return resultados[:limit]

        except Exception as e:
            print(f"❌ Erro ao buscar produtos inteligente: {e}")
            import traceback

            traceback.print_exc()
            return []

    def buscar_produto_por_termo(self, termo: str, produtos: Optional[List[Dict]] = None) -> Optional[Dict]:
        """
        Busca um produto usando busca inteligente no banco (produtos + receitas + combos).
        Se produtos for fornecido, também busca na lista como fallback.
        """
        if not termo or len(termo.strip()) < 2:
            return None

        termo = termo.strip()
        resultados_banco = self.buscar_produtos_inteligente(termo, limit=1)
        if resultados_banco:
            produto_encontrado = resultados_banco[0]
            print(
                f"✅ Produto encontrado no banco: {produto_encontrado['nome']} (tipo: {produto_encontrado.get('tipo', 'produto')})"
            )
            return produto_encontrado

        if produtos:
            termo_lower = termo.lower().strip()

            def remover_acentos(texto: str) -> str:
                acentos = {
                    "á": "a",
                    "à": "a",
                    "ã": "a",
                    "â": "a",
                    "é": "e",
                    "ê": "e",
                    "í": "i",
                    "ó": "o",
                    "ô": "o",
                    "õ": "o",
                    "ú": "u",
                    "ç": "c",
                }
                for acentuado, sem_acento in acentos.items():
                    texto = texto.replace(acentuado, sem_acento)
                return texto

            def normalizar(texto: str) -> str:
                texto = remover_acentos(texto.lower())
                return re.sub(r"[-\s_.]", "", texto)

            termo_sem_acento = remover_acentos(termo_lower)
            termo_normalizado = normalizar(termo_lower)

            for produto in produtos:
                nome_lower = produto["nome"].lower()
                nome_sem_acento = remover_acentos(nome_lower)
                if termo_lower == nome_lower or termo_sem_acento == nome_sem_acento:
                    print(f"✅ Match exato na lista: {produto['nome']}")
                    return produto

            for produto in produtos:
                nome_normalizado = normalizar(produto["nome"])
                if termo_normalizado == nome_normalizado:
                    print(f"✅ Match normalizado na lista: {produto['nome']}")
                    return produto

            for produto in produtos:
                nome_lower = produto["nome"].lower()
                nome_sem_acento = remover_acentos(nome_lower)
                nome_normalizado = normalizar(produto["nome"])
                if (
                    termo_sem_acento in nome_sem_acento
                    or termo_lower in nome_lower
                    or termo_normalizado in nome_normalizado
                ):
                    print(f"✅ Match parcial na lista (termo no nome): {produto['nome']}")
                    return produto

            for produto in produtos:
                nome_lower = produto["nome"].lower()
                nome_sem_acento = remover_acentos(nome_lower)
                palavras_nome = nome_sem_acento.split()
                for palavra in palavras_nome:
                    if len(palavra) > 3 and palavra in termo_sem_acento:
                        print(f"✅ Match por palavra '{palavra}' na lista: {produto['nome']}")
                        return produto

            mapeamento = {
                "coca": ["coca-cola", "coca cola", "cocacola"],
                "pepsi": ["pepsi"],
                "guarana": ["guarana", "guaraná"],
                "pizza": ["pizza"],
                "hamburguer": ["hamburguer", "hamburger", "burger", "burguer"],
                "x-": ["x-bacon", "x-tudo", "x-salada", "x-burguer"],
                "batata": ["batata", "fritas"],
                "calabresa": ["calabresa"],
                "frango": ["frango"],
                "bacon": ["bacon"],
            }

            for chave, variantes in mapeamento.items():
                if chave in termo_sem_acento or any(v in termo_sem_acento for v in variantes):
                    for produto in produtos:
                        nome_sem_acento = remover_acentos(produto["nome"].lower())
                        if chave in nome_sem_acento or any(v in nome_sem_acento for v in variantes):
                            print(f"✅ Match por mapeamento '{chave}' na lista: {produto['nome']}")
                            return produto

        print(f"❌ Produto não encontrado para termo: {termo}")
        return None

