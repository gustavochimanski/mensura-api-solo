# Proposta de melhoria do Chatbot (Roadmap)

## Fases

- [x] **Fase 1 — IA como roteador principal (Function Calling) + guardrails**  
  Objetivo: parar de “regex first”. A IA decide a função; regras ficam como proteção e fallback.

- [x] **Fase 2 — RAG (busca semântica) para catálogo/descrições**  
  Objetivo: responder perguntas abertas (“tem lactose?”, “qual é mais leve?”) com base na descrição/conhecimento.

- [x] **Fase 3 — Memória curta resumida + confirmação por confiança**  
  Objetivo: lidar melhor com ambiguidades (“esse”, “o último”, “o de frango”) e reduzir perguntas desnecessárias.

- [x] **Fase 4 — Observabilidade + suíte de regressão (conversas goldens)**  
  Objetivo: evoluir com segurança (métricas, logs estruturados, testes de conversas).

---

## Fase 1 — Especificação (o que é “feito”)

### Mudanças de arquitetura
- **IA (Groq) passa a ser a primeira tentativa** de interpretar intenção e escolher `funcao` via `tool_calls`.
- **Guardrails mínimos** acontecem antes da IA (ex.: `chamar_atendente`, `calcular_taxa_entrega`).
- **Fallback**: se IA falhar (timeout/erro) ou `GROQ_API_KEY` não estiver configurada, o sistema cai para as regras/agentes atuais.

### Critérios de aceite
- Com `GROQ_API_KEY` configurada: a maioria das mensagens comuns deve passar pelo caminho “IA primeiro”.
- Sem `GROQ_API_KEY`: comportamento antigo continua funcionando (regras/agentes).
- Guardrails devem “ganhar” da IA nos casos cobertos (ex.: cliente pede atendente).

---

## Status da execução
- **Fase 1**: _concluída_

---

## Fase 2 — Especificação (o que é “feito”)

### Mudanças de arquitetura
- Injetar **contexto do catálogo (RAG)** nos prompts:
  - **No roteamento (Function Calling)**: `_interpretar_intencao_ia` recebe um bloco “CONTEXTO DO CATÁLOGO (RAG)” com itens relevantes.
  - **No modo conversacional**: `_processar_conversa_ia` recebe um bloco “ITENS RELEVANTES DO CATÁLOGO (RAG)” para perguntas abertas.
- Quando `informar_sobre_produto` não achar o item, sugerir **possíveis matches** do catálogo em vez de “não achei”.

### Como o RAG funciona nesta fase
- **Retrieval**: usa `BuscaGlobalService.buscar(...)` (produtos/receitas/combos) com o texto da mensagem.
- **Augmentation**: formata os itens encontrados (nome/preço/descrição) e injeta no prompt.
- **Generation**: a IA responde usando as descrições (onde ficam os ingredientes).

### Critérios de aceite
- Perguntas abertas (“tem lactose?”, “o que tem?”, “qual é mais leve?”) têm mais chance de serem respondidas usando descrições do catálogo.
- Quando o nome do produto estiver “meio errado”, o bot sugere alternativas.

---

## Status da execução
- **Fase 2**: _concluída_

---

## Fase 3 — Especificação (o que é “feito”)

### Mudanças de arquitetura
- **Resolução de referências**: método `_resolver_referencias_na_mensagem` resolve:
  - "esse", "essa", "isso", "esse último" → substitui pelo último produto mencionado/adicionado
  - "o de [ingrediente]", "a de [ingrediente]" → substitui por produto que contém o ingrediente
- **Memória curta resumida**:
  - `_resumir_historico_para_ia`: limita histórico a N mensagens (padrão 8), priorizando recentes
  - `_resumir_contexto_pedido`: formata pedido de forma compacta e inteligente
- **Contexto melhorado**: histórico e pedido são resumidos antes de passar para a IA, reduzindo tokens e melhorando foco

### Como funciona
- **Antes de enviar para IA**: mensagem passa por resolução de referências
- **Histórico**: quando muito longo (>16 mensagens), mantém primeira (contexto) + últimas 8 (recentes)
- **Pedido**: formato compacto "2x Nome - R$ X.XX" com personalizações resumidas

### Critérios de aceite
- Mensagens com "esse", "o último" são resolvidas automaticamente
- Histórico longo não quebra o contexto (resumido inteligentemente)
- Pedido é apresentado de forma mais compacta e legível

---

## Status da execução
- **Fase 3**: _concluída_

---

## Fase 4 — Especificação (o que é “feito”)

### Mudanças de arquitetura
- **Módulo de observabilidade** (`observability.py`):
  - `ChatbotObservability`: classe para logs estruturados e métricas
  - Logs de decisões da IA (função escolhida, tempo, confiança)
  - Logs de erros e timeouts
  - Logs de fallback (quando usa regras/agentes)
  - Métricas agregadas (tempo médio, funções mais chamadas, etc)
- **Golden Tests** (testes de regressão):
  - `ConversaGoldenTest`: estrutura para definir testes de conversas
  - Funções para salvar/carregar testes em JSON
  - Conjunto de testes exemplo (adicionar produto, perguntas, referências, etc)
- **Integração no handler**:
  - Observabilidade inicializada por `user_id` em `processar_mensagem`
  - Logs automáticos em todas as decisões da IA
  - Métricas de tempo de resposta coletadas

### Como funciona
- **Logs estruturados**: todas as decisões da IA são logadas em JSON para análise posterior
- **Métricas em tempo real**: tempo médio de resposta, funções mais usadas, taxa de erros
- **Golden tests**: conjunto de conversas que devem sempre funcionar (validação de regressão)

### Critérios de aceite
- Logs estruturados disponíveis para análise (formato JSON)
- Métricas básicas coletadas (tempo, erros, funções)
- Estrutura de golden tests criada e documentada
- Sistema pronto para evoluir com segurança (detecta regressões)

### Arquivos criados
- `core/observability.py`: módulo completo de observabilidade
- `core/golden_tests/README.md`: documentação dos golden tests

---

## Status da execução
- **Fase 4**: _concluída_

---

## Resumo das 4 Fases

✅ **Fase 1**: IA como roteador principal (Function Calling)  
✅ **Fase 2**: RAG para catálogo/descrições  
✅ **Fase 3**: Memória curta resumida + resolução de referências  
✅ **Fase 4**: Observabilidade + golden tests  

**Todas as fases concluídas!** 🎉

