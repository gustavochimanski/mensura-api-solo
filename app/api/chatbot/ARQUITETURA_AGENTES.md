# 🤖 Arquitetura de Agentes do Chatbot

## 📊 Visão Geral

O sistema de chatbot utiliza uma **arquitetura híbrida** com:
- **3 Agentes Especializados** (detecção por regras/patterns)
- **IA Groq/LLaMA** (Function Calling para ações complexas)
- **Fallback com Regras** (quando agentes não detectam)

---

## 🎯 Agentes Especializados (Intention Agents)

### 1. **IniciarPedidoAgent** (Prioridade: 100)
**Responsabilidade:** Detectar quando o cliente quer INICIAR um novo pedido do zero.

**O que detecta:**
- "fazer novo pedido"
- "novo pedido"
- "começar de novo"
- "quero fazer pedido" (sem produto específico)
- "quero pedir" (sem produto específico)
- "iniciar pedido"

**O que NÃO detecta:**
- "fazer pedido de pizza" → vai para AdicionarProdutoAgent
- Mensagens com produto específico

**Função chamada:** `iniciar_novo_pedido`

---

### 2. **AdicionarProdutoAgent** (Prioridade: 50)
**Responsabilidade:** Detectar quando o cliente quer ADICIONAR um produto ao carrinho.

**O que detecta:**
- "quero X", "quero um X", "quero 2 X"
- "me ve X", "manda X", "traz X"
- "2 X", "um X", "duas X"
- "fazer pedido de X"
- "quero X sem Y" (com personalização)

**O que NÃO detecta:**
- Perguntas de preço ("quanto custa X?")
- Iniciar pedido genérico ("fazer novo pedido")

**Função chamada:** `adicionar_produto`

**Parâmetros extraídos:**
- `produto_busca`: Nome do produto
- `quantidade`: Quantidade (padrão: 1)
- `personalizacao`: Opcional (remover ingrediente ou adicionar extra)

---

### 3. **ConversacaoAgent** (Prioridade: 10)
**Responsabilidade:** Detectar saudações e conversas casuais (fallback).

**O que detecta:**
- Saudações: "oi", "olá", "eae", "bom dia", etc.
- Perguntas vagas: "o que tem?", "que que é bom?", "não sei"

**Função chamada:** `conversar`

**Parâmetros:**
- `tipo_conversa`: "saudacao" ou "pergunta_vaga"

---

## 🔄 Fluxo de Detecção de Intenções

```
Mensagem do Cliente
        ↓
Normalização (lowercase, sem acentos)
        ↓
┌─────────────────────────────────────┐
│  IntentionRouter (Agentes)          │
│  Ordem de verificação:               │
│  1. IniciarPedidoAgent (100)        │
│  2. AdicionarProdutoAgent (50)      │
│  3. ConversacaoAgent (10)            │
└─────────────────────────────────────┘
        ↓
    Detectou? ────SIM───→ Retorna intenção + função
        │
       NÃO
        ↓
┌─────────────────────────────────────┐
│  Fallback: Regras Simples           │
│  (_interpretar_intencao_regras)     │
│  - chamar_atendente                  │
│  - ver_cardapio                      │
│  - calcular_taxa_entrega            │
│  - informar_sobre_produto            │
│  - ver_carrinho                       │
│  - finalizar_pedido                   │
│  - remover_produto                    │
│  - personalizar_produto               │
│  - ver_adicionais                    │
│  - ver_combos                         │
└─────────────────────────────────────┘
        ↓
    Detectou? ────SIM───→ Retorna função
        │
       NÃO
        ↓
┌─────────────────────────────────────┐
│  IA Groq/LLaMA (Function Calling)   │
│  - Analisa contexto completo        │
│  - Histórico de mensagens            │
│  - Carrinho atual                    │
│  - Produtos disponíveis              │
│  - Escolhe função apropriada        │
└─────────────────────────────────────┘
        ↓
    Retorna função ou resposta textual
```

---

## 🛠️ Funções Disponíveis (Function Calling)

O sistema possui **13 funções** que podem ser chamadas pela IA ou pelos agentes:

### Funções de Pedido
1. **`adicionar_produto`** - Adiciona produto ao carrinho
2. **`remover_produto`** - Remove produto do carrinho
3. **`personalizar_produto`** - Personaliza produto já no carrinho
4. **`finalizar_pedido`** - Finaliza/fecha o pedido
5. **`iniciar_novo_pedido`** - Limpa carrinho e inicia novo pedido

### Funções de Consulta
6. **`ver_carrinho`** - Mostra carrinho atual
7. **`ver_cardapio`** - Lista produtos do cardápio
8. **`ver_combos`** - Lista combos disponíveis
9. **`ver_adicionais`** - Lista adicionais disponíveis
10. **`informar_sobre_produto`** - Informa sobre produto específico (ingredientes, preço, etc)

### Funções de Suporte
11. **`calcular_taxa_entrega`** - Calcula taxa de entrega
12. **`informar_sobre_estabelecimento`** - Informa horário/localização
13. **`chamar_atendente`** - Transfere para atendente humano

### Função de Conversa
14. **`conversar`** - Resposta conversacional (fallback)

---

## 📋 Resumo dos Agentes

| Agente | Prioridade | Detecta | Função Chamada |
|--------|------------|---------|----------------|
| **IniciarPedidoAgent** | 100 | Iniciar novo pedido | `iniciar_novo_pedido` |
| **AdicionarProdutoAgent** | 50 | Adicionar produto | `adicionar_produto` |
| **ConversacaoAgent** | 10 | Saudações/perguntas vagas | `conversar` |

---

## 🎯 Estratégia de Detecção

### 1. **Agentes Especializados (Primeiro)**
- Detecção rápida por patterns/regex
- Alta precisão para casos comuns
- Baixa latência

### 2. **Regras Simples (Fallback)**
- Cobre casos não cobertos pelos agentes
- Detecção por regex também
- Exemplos: chamar atendente, ver cardápio, taxa de entrega

### 3. **IA Groq/LLaMA (Último Recurso)**
- Usa contexto completo (histórico, carrinho, produtos)
- Function Calling para ações
- Melhor para casos ambíguos ou complexos

---

## 🔍 Exemplo de Fluxo Completo

**Mensagem:** "quero 2 pizzas calabresa"

1. **Normalização:** "quero 2 pizzas calabresa"
2. **IniciarPedidoAgent:** ❌ Não detecta (tem produto específico)
3. **AdicionarProdutoAgent:** ✅ Detecta!
   - Extrai: `produto_busca="pizza calabresa"`, `quantidade=2`
   - Retorna: `{"funcao": "adicionar_produto", "params": {...}}`
4. **Execução:** Adiciona 2 pizzas calabresa ao carrinho
5. **Resposta:** "✅ Adicionei 2x Pizza Calabresa ao seu pedido!"

---

## 📝 Notas Importantes

- **Prioridade importa:** Agentes são verificados na ordem de prioridade (maior primeiro)
- **Fallback inteligente:** Se agentes não detectam, usa regras e depois IA
- **Contexto:** IA tem acesso a histórico, carrinho e produtos para decisões melhores
- **Function Calling:** IA pode chamar funções diretamente, não apenas agentes
- **Extensibilidade:** Fácil adicionar novos agentes ao `IntentionRouter`

---

## 🚀 Como Adicionar Novo Agente

1. Criar classe herdando de `IntentionAgent`
2. Implementar método `detect()`
3. Definir prioridade no `__init__()`
4. Adicionar ao `IntentionRouter.agents[]`
5. Ordenação automática por prioridade

**Exemplo:**
```python
class MeuNovoAgent(IntentionAgent):
    def __init__(self):
        super().__init__(priority=75)  # Entre AdicionarProduto e Conversacao
    
    def detect(self, mensagem, mensagem_normalizada, context=None):
        # Sua lógica de detecção
        if re.search(r'meu_padrao', mensagem_normalizada):
            return {
                "intention": IntentionType.MINHA_INTENCAO,
                "funcao": "minha_funcao",
                "params": {}
            }
        return None
```
