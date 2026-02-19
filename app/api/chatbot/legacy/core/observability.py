"""
FASE 4: Observabilidade e métricas para o chatbot.
Logs estruturados, métricas de performance e rastreamento de decisões da IA.
"""
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    """Níveis de log"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ChatbotObservability:
    """Sistema de observabilidade para o chatbot"""
    
    def __init__(self, empresa_id: int, user_id: str = None):
        self.empresa_id = empresa_id
        self.user_id = user_id
        self.metrics = {
            "total_mensagens": 0,
            "total_erros": 0,
            "total_timeouts": 0,
            "funcoes_chamadas": {},
            "tempo_medio_resposta_ms": 0,
            "tempos_resposta": [],
        }
    
    def log_decisao_ia(
        self,
        mensagem: str,
        funcao_escolhida: str,
        params: Dict[str, Any],
        tempo_resposta_ms: float,
        confianca: Optional[float] = None,
        contexto_rag_usado: bool = False,
        referencias_resolvidas: List[str] = None,
    ) -> None:
        """
        Log estruturado de decisão da IA.
        
        Args:
            mensagem: Mensagem original do usuário
            funcao_escolhida: Função escolhida pela IA
            params: Parâmetros da função
            tempo_resposta_ms: Tempo de resposta em milissegundos
            confianca: Nível de confiança (0-1) se disponível
            contexto_rag_usado: Se usou RAG para buscar contexto
            referencias_resolvidas: Lista de referências resolvidas (ex: ["esse" -> "X-Bacon"])
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "empresa_id": self.empresa_id,
            "user_id": self.user_id,
            "tipo": "decisao_ia",
            "mensagem": mensagem[:200],  # Limita tamanho
            "funcao": funcao_escolhida,
            "params": params,
            "tempo_resposta_ms": round(tempo_resposta_ms, 2),
            "confianca": confianca,
            "contexto_rag_usado": contexto_rag_usado,
            "referencias_resolvidas": referencias_resolvidas or [],
        }
        
        # Log estruturado (pode ser enviado para sistema de logs)
        print(f"[OBSERVABILITY] {json.dumps(log_entry, ensure_ascii=False)}")
        
        # Atualiza métricas
        self.metrics["total_mensagens"] += 1
        self.metrics["funcoes_chamadas"][funcao_escolhida] = (
            self.metrics["funcoes_chamadas"].get(funcao_escolhida, 0) + 1
        )
        self.metrics["tempos_resposta"].append(tempo_resposta_ms)
        
        # Calcula tempo médio (mantém últimos 100)
        if len(self.metrics["tempos_resposta"]) > 100:
            self.metrics["tempos_resposta"] = self.metrics["tempos_resposta"][-100:]
        
        if self.metrics["tempos_resposta"]:
            self.metrics["tempo_medio_resposta_ms"] = sum(
                self.metrics["tempos_resposta"]
            ) / len(self.metrics["tempos_resposta"])
    
    def log_erro(
        self,
        mensagem: str,
        erro: Exception,
        contexto: Dict[str, Any] = None,
    ) -> None:
        """Log de erro estruturado"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "empresa_id": self.empresa_id,
            "user_id": self.user_id,
            "tipo": "erro",
            "mensagem": mensagem[:200],
            "erro_tipo": type(erro).__name__,
            "erro_mensagem": str(erro)[:500],
            "contexto": contexto or {},
        }
        
        print(f"[OBSERVABILITY-ERROR] {json.dumps(log_entry, ensure_ascii=False)}")
        self.metrics["total_erros"] += 1
    
    def log_timeout(
        self,
        mensagem: str,
        timeout_segundos: float,
    ) -> None:
        """Log de timeout"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "empresa_id": self.empresa_id,
            "user_id": self.user_id,
            "tipo": "timeout",
            "mensagem": mensagem[:200],
            "timeout_segundos": timeout_segundos,
        }
        
        print(f"[OBSERVABILITY-TIMEOUT] {json.dumps(log_entry, ensure_ascii=False)}")
        self.metrics["total_timeouts"] += 1
    
    def log_fallback(
        self,
        mensagem: str,
        motivo: str,
        funcao_fallback: str,
    ) -> None:
        """Log quando usa fallback (regras/agentes)"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "empresa_id": self.empresa_id,
            "user_id": self.user_id,
            "tipo": "fallback",
            "mensagem": mensagem[:200],
            "motivo": motivo,
            "funcao_fallback": funcao_fallback,
        }
        
        print(f"[OBSERVABILITY-FALLBACK] {json.dumps(log_entry, ensure_ascii=False)}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas atuais"""
        return {
            **self.metrics,
            "tempo_medio_resposta_ms": round(self.metrics["tempo_medio_resposta_ms"], 2),
        }
    
    def reset_metrics(self) -> None:
        """Reseta métricas (útil para testes)"""
        self.metrics = {
            "total_mensagens": 0,
            "total_erros": 0,
            "total_timeouts": 0,
            "funcoes_chamadas": {},
            "tempo_medio_resposta_ms": 0,
            "tempos_resposta": [],
        }


class ConversaGoldenTest:
    """
    Estrutura para testes de conversas (golden set).
    Permite validar que mudanças não quebram comportamentos esperados.
    """
    
    def __init__(self, nome: str, descricao: str = ""):
        self.nome = nome
        self.descricao = descricao
        self.mensagens: List[Dict[str, str]] = []  # [{"role": "user", "content": "..."}, ...]
        self.resultado_esperado: Dict[str, Any] = {}  # {"funcao": "...", "params": {...}}
        self.validacoes: List[str] = []  # Lista de validações a fazer
    
    def adicionar_mensagem(self, role: str, content: str) -> "ConversaGoldenTest":
        """Adiciona mensagem à conversa"""
        self.mensagens.append({"role": role, "content": content})
        return self
    
    def definir_resultado_esperado(
        self, funcao: str, params: Dict[str, Any] = None
    ) -> "ConversaGoldenTest":
        """Define resultado esperado"""
        self.resultado_esperado = {
            "funcao": funcao,
            "params": params or {},
        }
        return self
    
    def adicionar_validacao(self, validacao: str) -> "ConversaGoldenTest":
        """Adiciona validação customizada"""
        self.validacoes.append(validacao)
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dict (para salvar em arquivo)"""
        return {
            "nome": self.nome,
            "descricao": self.descricao,
            "mensagens": self.mensagens,
            "resultado_esperado": self.resultado_esperado,
            "validacoes": self.validacoes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversaGoldenTest":
        """Cria a partir de dict"""
        test = cls(data["nome"], data.get("descricao", ""))
        test.mensagens = data.get("mensagens", [])
        test.resultado_esperado = data.get("resultado_esperado", {})
        test.validacoes = data.get("validacoes", [])
        return test


def criar_golden_tests_exemplo() -> List[ConversaGoldenTest]:
    """
    Cria conjunto de testes golden de exemplo.
    Estes testes devem ser executados após mudanças para garantir regressão.
    """
    tests = []
    
    # Teste 1: Adicionar produto simples
    test1 = (
        ConversaGoldenTest(
            "adicionar_produto_simples",
            "Cliente pede um produto simples"
        )
        .adicionar_mensagem("user", "quero uma coca")
        .definir_resultado_esperado("adicionar_produto", {"produto_busca": "coca", "quantidade": 1})
    )
    tests.append(test1)
    
    # Teste 2: Pergunta sobre produto
    test2 = (
        ConversaGoldenTest(
            "pergunta_sobre_produto",
            "Cliente pergunta sobre ingredientes"
        )
        .adicionar_mensagem("user", "o que tem no x-bacon?")
        .definir_resultado_esperado("informar_sobre_produto", {"produto_busca": "x-bacon"})
    )
    tests.append(test2)
    
    # Teste 3: Resolução de referência
    test3 = (
        ConversaGoldenTest(
            "resolucao_referencia",
            "Cliente usa referência 'esse' após adicionar produto"
        )
        .adicionar_mensagem("user", "quero uma pizza")
        .adicionar_mensagem("assistant", "Anotado! 1 Pizza. Quer mais algo?")
        .adicionar_mensagem("user", "quanto fica esse?")
        .definir_resultado_esperado("informar_sobre_produto", {"produto_busca": "pizza"})
    )
    tests.append(test3)
    
    # Teste 4: Ver carrinho
    test4 = (
        ConversaGoldenTest(
            "ver_carrinho",
            "Cliente quer ver o carrinho"
        )
        .adicionar_mensagem("user", "o que eu pedi?")
        .definir_resultado_esperado("ver_carrinho", {})
    )
    tests.append(test4)
    
    return tests


def salvar_golden_tests(tests: List[ConversaGoldenTest], arquivo: str = "golden_tests.json") -> None:
    """Salva golden tests em arquivo JSON"""
    import os
    from pathlib import Path
    
    # Cria diretório se não existir
    dir_path = Path(__file__).parent / "golden_tests"
    dir_path.mkdir(exist_ok=True)
    
    arquivo_path = dir_path / arquivo
    with open(arquivo_path, "w", encoding="utf-8") as f:
        json.dump(
            [test.to_dict() for test in tests],
            f,
            ensure_ascii=False,
            indent=2,
        )
    
    print(f"✅ Golden tests salvos em: {arquivo_path}")


def carregar_golden_tests(arquivo: str = "golden_tests.json") -> List[ConversaGoldenTest]:
    """Carrega golden tests de arquivo JSON"""
    from pathlib import Path
    
    dir_path = Path(__file__).parent / "golden_tests"
    arquivo_path = dir_path / arquivo
    
    if not arquivo_path.exists():
        return []
    
    with open(arquivo_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return [ConversaGoldenTest.from_dict(item) for item in data]
