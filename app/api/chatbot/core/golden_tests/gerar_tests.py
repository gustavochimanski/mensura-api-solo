"""
Script para gerar golden tests iniciais.
Execute: python -m app.api.chatbot.core.golden_tests.gerar_tests
"""
from pathlib import Path
import sys

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from app.api.chatbot.core.observability import criar_golden_tests_exemplo, salvar_golden_tests

if __name__ == "__main__":
    print("📝 Gerando golden tests de exemplo...")
    tests = criar_golden_tests_exemplo()
    salvar_golden_tests(tests, "golden_tests.json")
    print(f"✅ {len(tests)} golden tests criados com sucesso!")
