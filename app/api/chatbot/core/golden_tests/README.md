# Golden Tests - Testes de Regressão do Chatbot

## O que são Golden Tests?

Golden tests são **conversas de exemplo** que validam comportamentos esperados do chatbot. Eles garantem que mudanças no código não quebrem funcionalidades existentes.

## Estrutura

Cada teste contém:
- **Nome**: Identificador único do teste
- **Descrição**: O que o teste valida
- **Mensagens**: Sequência de mensagens (user/assistant)
- **Resultado esperado**: Função e parâmetros que devem ser retornados
- **Validações**: Validações customizadas (opcional)

## Como usar

### Criar novos testes

```python
from app.api.chatbot.core.observability import ConversaGoldenTest

test = (
    ConversaGoldenTest("meu_teste", "Descrição do teste")
    .adicionar_mensagem("user", "quero uma pizza")
    .definir_resultado_esperado("adicionar_produto", {"produto_busca": "pizza", "quantidade": 1})
)
```

### Executar testes

```python
from app.api.chatbot.core.observability import carregar_golden_tests
from app.api.chatbot.core.groq_sales_handler import GroqSalesHandler

# Carrega testes
tests = carregar_golden_tests()

# Executa cada teste
for test in tests:
    handler = GroqSalesHandler(db, empresa_id=1)
    # Simula conversa e valida resultado
    # ...
```

## Testes incluídos

1. **adicionar_produto_simples**: Cliente pede um produto simples
2. **pergunta_sobre_produto**: Cliente pergunta sobre ingredientes
3. **resolucao_referencia**: Cliente usa referência "esse" após adicionar produto
4. **ver_carrinho**: Cliente quer ver o carrinho

## Adicionar novos testes

Edite `golden_tests.json` ou use a função `salvar_golden_tests()` do módulo `observability.py`.
