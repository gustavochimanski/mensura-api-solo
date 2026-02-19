"""
Políticas e guardrails para reduzir alucinação e aumentar consistência do LLM.

Objetivos:
- Injetar regras de confiabilidade (não inventar, perguntar quando faltar dados, separar fato/suposição)
- Padronizar extração/validação de JSON quando a resposta deveria ser um objeto
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

import json
import re


DEFAULT_MAX_TEMPERATURE = 0.4


RELIABILITY_POLICY_PT = """REGRAS DE CONFIABILIDADE (anti-alucinação):
- Não invente fatos, preços, produtos, regras, IDs, nomes de tabelas, endpoints ou informações não presentes no contexto.
- Se faltar informação para responder corretamente, faça perguntas objetivas antes de concluir.
- Se houver ambiguidade, peça esclarecimento (ex.: qual produto/tamanho/quantidade).
- Quando não tiver certeza, diga explicitamente "Não tenho dados suficientes" e peça o dado necessário.
- Nunca chute números/valores. Só cite números se estiverem no contexto.
"""


JSON_ONLY_POLICY_PT = """FORMATO:
- Retorne APENAS JSON válido (um único objeto), sem texto fora do JSON.
"""


def clamp_temperature(value: Optional[float], *, max_temperature: float = DEFAULT_MAX_TEMPERATURE) -> float:
    """
    Mantém temperatura dentro de limites seguros para reduzir alucinação.
    Se vier None ou inválido, retorna um padrão conservador.
    """
    try:
        temp = float(value) if value is not None else 0.2
    except Exception:
        temp = 0.2
    if temp < 0.0:
        return 0.0
    if temp > max_temperature:
        return max_temperature
    return temp


def build_system_prompt(base_prompt: str, *, require_json_object: bool = False) -> str:
    """
    Injeta política de confiabilidade ao final do prompt de sistema.
    Opcionalmente força instrução de JSON-only.
    """
    base_prompt = (base_prompt or "").strip()
    parts = [base_prompt, "", RELIABILITY_POLICY_PT.strip()]
    if require_json_object:
        parts.extend(["", JSON_ONLY_POLICY_PT.strip()])
    return "\n".join([p for p in parts if p is not None]).strip()


def extract_first_json_object(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Tenta extrair o primeiro objeto JSON do texto.
    Retorna (obj, json_str) ou (None, None) se falhar.
    """
    if not text:
        return None, None

    cleaned = text.strip()
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    # Caso já seja JSON puro
    if cleaned.startswith("{") and cleaned.endswith("}"):
        try:
            return json.loads(cleaned), cleaned
        except Exception:
            pass

    # Procura um bloco JSON no meio do texto
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None, None

    candidate = cleaned[start : end + 1].strip()
    try:
        return json.loads(candidate), candidate
    except Exception:
        return None, None


def validate_action_json(
    payload: Dict[str, Any],
    *,
    allowed_actions: Iterable[str],
    require_resposta: bool = True,
) -> Tuple[bool, str]:
    """
    Valida o JSON retornado pela IA no formato esperado pelo fluxo conversacional.
    Retorna (ok, motivo).
    """
    if not isinstance(payload, dict):
        return False, "Payload não é um objeto JSON"

    if require_resposta:
        resposta = payload.get("resposta")
        if not isinstance(resposta, str) or not resposta.strip():
            return False, 'Campo "resposta" ausente ou inválido'

    acao = payload.get("acao", "nenhuma")
    if not isinstance(acao, str) or acao not in set(allowed_actions):
        return False, f'Ação inválida em "acao": {acao!r}'

    itens = payload.get("itens", [])
    if itens is None:
        itens = []
    if not isinstance(itens, list):
        return False, 'Campo "itens" deve ser uma lista'

    # Regra crítica já usada no código: se acao == adicionar, itens não pode ser vazio
    if acao == "adicionar" and len(itens) == 0:
        return False, 'Ação "adicionar" exige "itens" não vazio'

    return True, "ok"


def make_json_repair_prompt(*, allowed_actions: Iterable[str]) -> str:
    allowed = " | ".join([f'"{a}"' for a in allowed_actions])
    return (
        "Você é um reparador/validador de JSON. "
        "Sua tarefa é devolver APENAS um objeto JSON válido, sem texto extra. "
        "Se algo estiver faltando, preencha com valores seguros.\n\n"
        "Regras:\n"
        f'- "acao" deve ser um dentre: {allowed}\n'
        '- Se "acao" == "adicionar", "itens" NÃO pode ser vazio.\n'
        '- "resposta" deve ser uma string curta.\n'
    )

