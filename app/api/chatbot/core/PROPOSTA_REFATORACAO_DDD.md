# Proposta de Refatoração: Divisão do `groq_sales_handler.py` seguindo DDD

## 📊 Situação Atual

- **Arquivo**: `groq_sales_handler.py` (~7882 linhas)
- **Classe**: `GroqSalesHandler` com ~99 métodos
- **Problema**: Arquivo muito grande, difícil de manter e testar

## 🎯 Objetivo

Dividir o arquivo em múltiplos módulos seguindo **Domain-Driven Design (DDD)**, separando responsabilidades e facilitando manutenção.

## 🏗️ Estrutura Proposta

## ✅ Progresso (checklist)

- [x] `utils/mensagem_utils.py` (criado e em uso)
- [x] `utils/mensagem_formatters.py` (criado e em uso via delegação no handler)
- [x] `utils/config_loader.py` (criado e em uso via delegação no handler)
- [x] `domain/produto_service.py` (criado e em uso via delegação no handler)
- [x] `domain/carrinho_service.py` (criado e em uso via delegação no handler)
- [ ] `domain/pedido_service.py`
- [ ] `domain/endereco_domain_service.py`
- [ ] `domain/pagamento_service.py`
- [ ] `application/conversacao_service.py`
- [ ] `application/groq_sales_orchestrator.py`
- [ ] `infrastructure/groq_llm_adapter.py`
- [ ] `infrastructure/intencao_interpreter.py`

### 1. **Domain Services** (Lógica de Negócio)

#### `domain/produto_service.py`
**Responsabilidade**: Busca, normalização e manipulação de produtos

**Métodos a mover**:
- [x] `_buscar_produto_por_termo()` (delegado para `ProdutoDomainService`)
- [x] `_buscar_todos_produtos()` (delegado para `ProdutoDomainService`)
- [x] `_buscar_produtos()` (delegado para `ProdutoDomainService`)
- [x] `_buscar_produtos_inteligente()` (delegado para `ProdutoDomainService`)
- [x] `_normalizar_termo_busca()` (delegado para `ProdutoDomainService`)
- [x] `_corrigir_termo_busca()` (delegado para `ProdutoDomainService`)
- [x] `_expandir_sinonimos()` (delegado para `ProdutoDomainService`)
- [ ] `_resolver_produto_para_preco()` (ainda no handler)
- [ ] `_detectar_produto_na_mensagem()` (ainda no handler)
- [x] `_buscar_promocoes()` (delegado para `ProdutoDomainService`)

**Dependências**:
- `ProdutoAdapter`
- `ComboAdapter`
- Banco de dados

---

#### `domain/carrinho_service.py`
**Responsabilidade**: Operações de carrinho (adicionar, remover, formatar)

**Métodos a mover**:
- [x] `_adicionar_ao_carrinho()` (delegado para `CarrinhoDomainService`)
- [x] `_remover_do_carrinho()` (delegado para `CarrinhoDomainService`)
- [x] `_personalizar_item_carrinho()` (delegado para `CarrinhoDomainService`)
- [x] `_formatar_carrinho()` (delegado para `MensagemFormatters`)
- [x] `_verificar_carrinho_aberto()` (delegado para `CarrinhoDomainService`)
- [x] `_formatar_mensagem_carrinho_aberto()` (delegado para `CarrinhoDomainService`)
- [x] `_carrinho_response_para_lista()` (delegado para `CarrinhoDomainService`)
- [x] `_sincronizar_carrinho_dados()` (delegado para `CarrinhoDomainService`)
- [x] `_montar_item_carrinho_request()` (delegado para `CarrinhoDomainService`)
- [x] `_converter_contexto_para_carrinho()` (delegado para `CarrinhoDomainService`)
- [x] `_get_carrinho_service()` (delegado para `CarrinhoDomainService`)
- [x] `_obter_carrinho_db()` (delegado para `CarrinhoDomainService`)

**Dependências**:
- `CarrinhoService`
- Schemas de carrinho

---

#### `domain/pedido_service.py`
**Responsabilidade**: Criação, finalização e gerenciamento de pedidos

**Métodos a mover**:
- `_salvar_pedido_no_banco()`
- `_salvar_pedido_via_checkout()`
- `_gerar_resumo_pedido()`
- `_cancelar_pedido()`
- `_detectar_confirmacao_cancelamento()`
- `_detectar_confirmacao_cancelamento_carrinho()`

**Dependências**:
- Repositório de pedidos
- Serviços de checkout

---

#### `domain/endereco_domain_service.py`
**Responsabilidade**: Lógica de negócio de endereços (complementa `address_service.py`)

**Métodos a mover**:
- `_iniciar_fluxo_endereco()`
- `_processar_selecao_endereco_salvo()`
- `_processar_busca_endereco_google()`
- `_processar_selecao_endereco_google()`
- `_processar_complemento()`
- `_parece_endereco()`
- `_extrair_endereco_com_ia()`

**Dependências**:
- `ChatbotAddressService` (já existe)

---

#### `domain/pagamento_service.py`
**Responsabilidade**: Lógica de pagamento e meios de pagamento

**Métodos a mover**:
- `_buscar_meios_pagamento()`
- `_detectar_forma_pagamento_em_mensagem()`
- `_detectar_forma_pagamento_natural()`
- `_processar_pagamento()`
- `_mensagem_formas_pagamento()`
- `_ir_para_pagamento_ou_resumo()`

**Dependências**:
- Banco de dados (meios_pagamento)

---

### 2. **Application Services** (Orquestração)

#### `application/groq_sales_orchestrator.py`
**Responsabilidade**: Orquestra o fluxo principal de processamento de mensagens

**Métodos a mover**:
- `processar_mensagem()` (método principal)
- `_processar_conversa_ia()`
- `_processar_entrega_ou_retirada()`
- `_perguntar_entrega_ou_retirada()`
- `_nao_entendeu_mensagem()`

**Dependências**:
- Todos os Domain Services
- `IntencaoInterpreter`
- `GroqLLMAdapter`

---

#### `application/conversacao_service.py`
**Responsabilidade**: Gerencia estado da conversa e histórico

**Métodos a mover**:
- `_obter_estado_conversa()`
- `_salvar_estado_conversa()`
- `_montar_contexto()`
- `_eh_primeira_mensagem()`
- `_processar_cadastro_nome_rapido()`

**Dependências**:
- Banco de dados (estado da conversa)

---

### 3. **Infrastructure/Adapters** (Integrações Externas)

#### `infrastructure/groq_llm_adapter.py`
**Responsabilidade**: Comunicação com Groq API

**Métodos a mover**:
- `_interpretar_intencao_ia()`
- `_gerar_resposta_conversacional()`
- `_gerar_resposta_sobre_produto()`
- `_calcular_e_responder_taxa_entrega()`
- `_fallback_resposta_inteligente()`
- `_formatar_cardapio_para_ia()`

**Dependências**:
- Groq API
- `sales_prompts.py`

---

#### `infrastructure/intencao_interpreter.py`
**Responsabilidade**: Interpretação de intenções (regras + IA)

**Métodos a mover**:
- `_interpretar_intencao_regras()`
- Métodos de detecção:
  - `_detectar_confirmacao_pedido()`
  - `_detectar_nao_quer_falar_pedido()`
  - `_detectar_negacao()`
  - `_detectar_pedido_cardapio()`
  - `_detectar_ver_carrinho()`
  - `_detectar_remocao_produto()`
  - `_detectar_entrega()`
  - `_detectar_retirada()`
  - `_detectar_confirmacao_adicao()`
  - `_detectar_novo_endereco()`

**Dependências**:
- `ProdutoDomainService`
- `CarrinhoDomainService`

---

### 4. **Value Objects/Helpers** (Utilitários)

#### `utils/mensagem_utils.py`
**Responsabilidade**: Normalização e extração de dados de mensagens

**Métodos a mover**:
- [x] `_normalizar_mensagem()` (movido para `MensagemUtils.normalizar_mensagem`)
- [x] `_extrair_quantidade()` (movido para `MensagemUtils.extrair_quantidade`)
- [x] `_extrair_quantidade_pergunta()` (movido para `MensagemUtils.extrair_quantidade_pergunta`)
- [x] `_extrair_itens_pergunta_preco()` (movido para `MensagemUtils.extrair_itens_pergunta_preco`)
- [x] `_extrair_itens_pedido()` (movido para `MensagemUtils.extrair_itens_pedido`)
- [x] `_extrair_numero()` (movido para `MensagemUtils.extrair_numero`)
- [x] `_extrair_numero_natural()` (movido para `MensagemUtils.extrair_numero_natural`)

**Dependências**:
- Nenhuma (funções puras)

---

#### `utils/mensagem_formatters.py`
**Responsabilidade**: Formatação de mensagens para o usuário

**Métodos a mover**:
- [x] `_gerar_mensagem_boas_vindas()` (delegado para `MensagemFormatters`)
- [x] `_gerar_mensagem_boas_vindas_conversacional()` (delegado para `MensagemFormatters`)
- [x] `_gerar_lista_produtos()` (delegado para `MensagemFormatters`)
- [ ] `_gerar_resposta_preco_itens()` (ainda no handler)
- [x] `_formatar_horarios_funcionamento()` (delegado para `MensagemFormatters`)
- [x] `_formatar_localizacao_empresas()` (delegado para `MensagemFormatters`)
- [x] `_buscar_empresas_ativas()` (delegado para `MensagemFormatters`)

**Dependências**:
- Dados do banco

---

#### `utils/config_loader.py`
**Responsabilidade**: Carregamento de configurações

**Métodos a mover**:
- [x] `_load_chatbot_config()` (delegado para `ConfigLoader`)
- [x] `_get_chatbot_config()` (delegado para `ConfigLoader`)
- [x] `_obter_link_cardapio()` (delegado para `ConfigLoader`)
- [x] `_obter_mensagem_final_pedido()` (delegado para `ConfigLoader`)

**Dependências**:
- Banco de dados (configurações)

---

### 5. **Main Handler** (Ponto de Entrada)

#### `groq_sales_handler.py` (refatorado)
**Responsabilidade**: Coordena todos os serviços, mantém interface pública

**Estrutura**:
```python
class GroqSalesHandler:
    def __init__(self, db: Session, empresa_id: int, ...):
        # Inicializa todos os serviços
        self.produto_service = ProdutoDomainService(db, empresa_id)
        self.carrinho_service = CarrinhoDomainService(db, empresa_id)
        self.pedido_service = PedidoDomainService(db, empresa_id)
        self.endereco_service = EnderecoDomainService(db, empresa_id)
        self.pagamento_service = PagamentoDomainService(db, empresa_id)
        self.conversacao_service = ConversacaoService(db, empresa_id)
        self.intencao_interpreter = IntencaoInterpreter(...)
        self.groq_adapter = GroqLLMAdapter(...)
        self.orchestrator = GroqSalesOrchestrator(...)
    
    async def processar_mensagem(self, user_id: str, mensagem: str, ...):
        return await self.orchestrator.processar_mensagem(user_id, mensagem, ...)
```

---

## 📁 Estrutura de Diretórios Proposta

```
core/
├── groq_sales_handler.py          # Handler principal (refatorado, ~200 linhas)
├── domain/
│   ├── __init__.py
│   ├── produto_service.py         # ~500 linhas
│   ├── carrinho_service.py         # ~600 linhas
│   ├── pedido_service.py           # ~400 linhas
│   ├── endereco_domain_service.py # ~300 linhas
│   └── pagamento_service.py        # ~300 linhas
├── application/
│   ├── __init__.py
│   ├── groq_sales_orchestrator.py  # ~800 linhas
│   └── conversacao_service.py      # ~400 linhas
├── infrastructure/
│   ├── __init__.py
│   ├── groq_llm_adapter.py         # ~1000 linhas
│   └── intencao_interpreter.py     # ~1500 linhas
└── utils/
    ├── __init__.py
    ├── mensagem_utils.py           # ~300 linhas
    ├── mensagem_formatters.py      # ~500 linhas
    └── config_loader.py            # ~150 linhas
```

---

## 🔄 Fluxo de Processamento

```
processar_mensagem_groq()
    ↓
GroqSalesHandler.processar_mensagem()
    ↓
GroqSalesOrchestrator.processar_mensagem()
    ↓
IntencaoInterpreter.interpretar()  (regras ou IA)
    ↓
Domain Services executam ações
    ↓
Formatters geram resposta
    ↓
Retorna resposta
```

---

## ✅ Benefícios

1. **Separação de Responsabilidades**: Cada módulo tem uma responsabilidade clara
2. **Testabilidade**: Fácil criar testes unitários para cada serviço
3. **Manutenibilidade**: Mudanças isoladas em módulos específicos
4. **Reutilização**: Serviços podem ser reutilizados em outros contextos
5. **Escalabilidade**: Fácil adicionar novos recursos sem aumentar arquivos existentes
6. **DDD Compliance**: Segue princípios de Domain-Driven Design

---

## 🚀 Plano de Implementação

1. **Fase 1**: Criar estrutura de diretórios e arquivos vazios
2. **Fase 2**: Mover métodos utilitários (utils) - baixo risco
3. **Fase 3**: Mover Domain Services - médio risco
4. **Fase 4**: Mover Application Services - médio risco
5. **Fase 5**: Mover Infrastructure - alto risco (testar bem)
6. **Fase 6**: Refatorar handler principal
7. **Fase 7**: Testes e ajustes finais

---

## ⚠️ Considerações

- **Compatibilidade**: Manter interface pública do `GroqSalesHandler` igual
- **Dependências Circulares**: Evitar importações circulares entre módulos
- **Testes**: Criar testes para cada módulo antes de mover
- **Incremental**: Fazer migração incremental, não tudo de uma vez

---

## 🧭 Mapa do Domínio (Ubiquitous Language)

Para reduzir ambiguidade e “if-else” espalhado, vale padronizar termos no código e na documentação:

- **Conversa**: interação contínua com o usuário (histórico, estado, contexto).
- **Intenção**: o que o usuário quer fazer (ex.: adicionar item, ver carrinho, finalizar).
- **Carrinho**: agregação de itens selecionados, personalizações e totais parciais.
- **Item de Carrinho**: produto/receita/combo + quantidade + personalização.
- **Pedido**: confirmação do carrinho + entrega/retirada + pagamento + persistência.
- **Entrega/Retirada**: modalidade de recebimento.
- **Endereço**: destino (salvo/novo), complemento, validações e cálculo de taxa.
- **Pagamento**: método (PIX/cartão/dinheiro), troco e regras de validação.
- **Catálogo**: produtos/receitas/combos/complementos/adicionais.

---

## 🧱 Bounded Contexts (limites sugeridos)

Embora o código esteja dentro de `app/api/chatbot`, o domínio real cruza módulos (catálogo, pedidos, cadastros). Para DDD “prático”, a refatoração pode tratar estes limites como *subdomínios* dentro do chatbot, com fronteiras claras:

1. **Conversação** (Contexto de Conversa)
   - Mantém estado, histórico e “onde o usuário está” no fluxo.
2. **Intenção** (Contexto de Interpretação)
   - Regras + IA para mapear mensagem → intenção + parâmetros.
3. **Catálogo** (Contexto de Produtos)
   - Resolver produto/receita/combo e suas variações.
4. **Carrinho** (Contexto de Seleção)
   - Operações de adicionar/remover/personalizar, sincronizar e formatar.
5. **Checkout/Pedido** (Contexto de Fechamento)
   - Montar preview, calcular totais, persistir/finalizar/cancelar.
6. **Entrega/Endereço** (Contexto de Logística)
   - Endereço salvo/novo, validação, complemento, cálculo de taxa.
7. **Pagamento** (Contexto Financeiro)
   - Métodos, validações, mensagens e estado.

**Regra de ouro**: cada contexto expõe **interfaces pequenas** (portas) para o orquestrador, e implementa integrações externas via adapters (infrastructure), reduzindo acoplamento.

---

## 🧩 Padrões táticos DDD (o que “entra” em cada camada)

### Entidades e Agregados (proposta mínima)

- **Aggregate `Carrinho` (Aggregate Root)**
  - Contém `ItensCarrinho` e regras como: somar quantidade, evitar duplicidade por “mesmo produto + mesma personalização”, limites e validações.
  - A persistência pode continuar no serviço atual, mas a **regra** deve sair do handler.

- **Entidade `Conversa`**
  - `user_id`, `estado`, `metadata` (contexto), timestamps.

- **Entidade `Pedido`**
  - `pedido_id`, `status`, `itens`, `taxa_entrega`, totais, `pagamento`, `entrega/retirada`.

### Value Objects (VOs) úteis (sem exagero)

- `Telefone` (normalização/validação)
- `Dinheiro` (operações com centavos para evitar float, se/quando fizer sentido)
- `EnderecoTexto` / `EnderecoSelecionado` (texto + complemento + referência)
- `FormaPagamento` (enum/validador)

### Domain Services (regra que não cabe numa entidade)

- `ProdutoDomainService` ✅ já existe (busca/normalização/heurísticas)
- `CarrinhoDomainService` ✅ já existe (operações do carrinho)
- `PedidoDomainService` ⏳ (preview/finalização/cancelamento/resumo)
- `EnderecoDomainService` ⏳ (fluxo e validações de endereço; pode reutilizar `ChatbotAddressService` como dependência)
- `PagamentoDomainService` ⏳ (detecção de forma, validação e mensagens)

---

## 🔌 Ports & Adapters (interfaces para desacoplar)

Mesmo mantendo SQLAlchemy e chamadas HTTP, a refatoração ganha muito criando interfaces (contratos) simples, com implementações em `infrastructure/`.

### Ports (contratos sugeridos)

- `ConversaRepository`
  - `obter_ultima(user_id)`, `salvar_estado(user_id, estado, metadata)`
- `CarrinhoRepository`
  - `obter(user_id)`, `salvar(carrinho)`, `limpar(user_id)`
- `PedidoRepository`
  - `salvar(pedido)`, `cancelar(pedido_id)`
- `CatalogoGateway`
  - `buscar_produtos(termo)`, `resolver_produto(termo)`, `buscar_combos(...)` etc.
- `CheckoutGateway`
  - `criar_preview(payload)`, `finalizar(payload)`
- `LLMGateway`
  - `interpretar_intencao(contexto)`, `gerar_resposta(...)`
- `GeocodingGateway` (se aplicável)
  - buscar/selecionar endereço no provedor (Google etc.)

### Implementações (infrastructure)

- `infrastructure/*Repository` usando SQLAlchemy/text query (como já está sendo feito)
- `infrastructure/http_checkout_gateway.py` usando `httpx`
- `infrastructure/groq_llm_adapter.py` usando a API Groq
- `infrastructure/google_maps_gateway.py` (se existir uso)

**Anti-Corruption Layer (ACL)**: qualquer retorno externo deve ser traduzido para modelos/DTOs internos (evita espalhar “shape” de APIs no domínio).

---

## 🧠 Application Layer (casos de uso)

Em vez do handler ter 99 métodos, o ideal é concentrar “o que fazer” em casos de uso pequenos:

- `ProcessarMensagem` (orquestra intenção → ação → resposta)
- `AdicionarProdutoAoCarrinho`
- `RemoverProdutoDoCarrinho`
- `PersonalizarItemCarrinho`
- `VerCarrinho`
- `IniciarFinalizacao` (garante endereço e pagamento antes)
- `FinalizarPedido`

O `GroqSalesOrchestrator` pode ser o “Application Service” principal, chamando esses use-cases e delegando regras ao domínio.

---

## 🧪 Estratégia de Testes (para não quebrar produção)

### Testes unitários (alto retorno)

- `MensagemUtils` (regex/extrações) — testes com vários textos reais
- `ProdutoDomainService.normalizar_termo_busca` e heurísticas
- `CarrinhoDomainService` (adicionar/remover/personalizar) com cenários de borda

### Testes de integração (foco em regressão)

- `GroqSalesHandler.processar_mensagem()` com stubs/mocks dos gateways (`LLMGateway`, `CheckoutGateway`)
- Persistência de estado (conversa/carrinho) em banco de teste

### Golden tests (recomendado para chatbot)

Criar um conjunto de **conversas “ouro”** (mensagem → intenção → resposta esperada) e rodar sempre que mover método. Isso reduz risco ao refatorar arquivos grandes.

---

## 🛰️ Observabilidade (mínimo para depurar)

- **Correlation id** por `user_id` + timestamp/uuid em logs.
- Logs estruturados (JSON) com: `empresa_id`, `user_id`, `intent`, `state`, `latency_ms`, `erro`.
- Métrica simples: contagem por intenção + erro por gateway (Groq/Checkout/Google).

---

## 🧩 Plano de migração incremental (mais detalhado)

### Fase A — “blindagem” antes de mover (1–2 dias)

- Adicionar logs estruturados no fluxo atual (sem refatorar lógica).
- Criar golden tests com 20–50 conversas reais (anônimas).

### Fase B — completar o domínio (2–5 dias)

- Implementar `PedidoDomainService`, `EnderecoDomainService`, `PagamentoDomainService` **inicialmente como wrappers** chamando o que já existe no handler (sem alterar comportamento).
- Migrar método por método do handler para esses serviços, mantendo delegação.

### Fase C — application/infrastructure (3–7 dias)

- Criar `GroqLLMAdapter` e `IntencaoInterpreter` como módulos separados.
- Extrair `CheckoutGateway` e `ConversaRepository` do handler.
- `GroqSalesHandler` vira fachada fina (constrói dependências e chama `orchestrator.processar_mensagem`).

### Fase D — limpeza e padronização (contínuo)

- Remover código morto/duplicado.
- Padronizar nomes e contratos (evitar múltiplas funções para a mesma intenção).
- Reduzir acoplamento com SQL/text em camadas acima de infrastructure.

---

## ✅ Critérios de sucesso (Definition of Done)

- `groq_sales_handler.py` reduzido para **fachada/orquestração mínima** (ideal: < 500 linhas).
- Serviços por domínio com responsabilidade única e testes cobrindo regras críticas.
- Nenhuma regressão nos golden tests (ou regressões explicadas e aprovadas).
- Integrações externas isoladas em `infrastructure/` com contratos claros.

---

## 🗂️ Inventário do que ainda está no `groq_sales_handler.py` (alvos imediatos)

Com base nos métodos atualmente no handler, estes são os “blocos” que mais valem ser extraídos (por coesão e redução de risco):

### 1) Preço/Detecção de produto em mensagem (Catálogo + Mensagens)

- `def _resolver_produto_para_preco(...)` (linha ~737)
  - **Destino sugerido**: `domain/produto_service.py` (ou `application/precos_service.py` se misturar regra + apresentação).
- `def _gerar_resposta_preco_itens(...)` (linha ~755)
  - **Destino sugerido**: `utils/mensagem_formatters.py` (formatação) + um caso de uso `application/consultar_preco_usecase.py` (orquestração).
- `def _detectar_produto_na_mensagem(...)` (linha ~3884)
  - **Destino sugerido**: `infrastructure/intencao_interpreter.py` (detecção/regra) **ou** `domain/produto_service.py` (se for heurística de resolução).

### 2) Pedido/Checkout (Checkout/Pedido)

- `async def _gerar_resumo_pedido(...)` (linha ~4999)
  - **Destino sugerido**: `domain/pedido_service.py` (montagem de resumo) + `utils/mensagem_formatters.py` (texto final).
- `async def _salvar_pedido_via_checkout(...)` (linha ~5085)
  - **Destino sugerido**: `infrastructure/http_checkout_gateway.py` + caso de uso `application/finalizar_pedido_usecase.py`.
- `def _salvar_pedido_no_banco(...)` (linha ~5210)
  - **Destino sugerido**: `infrastructure/pedido_repository.py` (SQL) + `domain/pedido_service.py` (regras).
- `async def _cancelar_pedido(...)` (linha ~3662)
  - **Destino sugerido**: `application/cancelar_pedido_usecase.py` + repository/gateway.

### 3) Endereço/Entrega/Retirada (Logística)

- `async def _iniciar_fluxo_endereco(...)` (linha ~4618)
- `async def _processar_selecao_endereco_salvo(...)` (linha ~4656)
- `async def _processar_busca_endereco_google(...)` (linha ~4701)
- `async def _processar_selecao_endereco_google(...)` (linha ~4753)
- `async def _processar_complemento(...)` (linha ~4785)
- `def _perguntar_entrega_ou_retirada(...)` (linha ~4889)
- `async def _processar_entrega_ou_retirada(...)` (linha ~4936)

**Destino sugerido**: `domain/endereco_domain_service.py` (fluxo/regras) + `infrastructure/google_maps_gateway.py` (se houver) + `application/definir_entrega_usecase.py`.

### 4) Pagamento (Financeiro)

- `def _buscar_meios_pagamento(...)` (linha ~455)
  - **Destino sugerido**: `infrastructure/pagamento_repository.py` (ou gateway) + `domain/pagamento_service.py`.
- `async def _processar_pagamento(...)` (linha ~4968)
  - **Destino sugerido**: `domain/pagamento_service.py` + `application/definir_pagamento_usecase.py`.

### 5) Estado de conversa (Conversação)

- `def _obter_estado_conversa(...)` (linha ~4368)
- `def _salvar_estado_conversa(...)` (linha ~4427)
- `async def _processar_cadastro_nome_rapido(...)` (linha ~4313)

**Destino sugerido**: `application/conversacao_service.py` + `infrastructure/conversa_repository.py`.

---

## 🧾 Matriz “método → módulo” (resumo operacional)

| Responsabilidade | Hoje | Amanhã (sugerido) |
|---|---|---|
| Resolução de produto p/ preço | `_resolver_produto_para_preco` | `domain/produto_service.py` |
| Resposta de preços | `_gerar_resposta_preco_itens` | `application/consultar_preco_*` + `utils/mensagem_formatters.py` |
| Detecção de produto na mensagem | `_detectar_produto_na_mensagem` | `infrastructure/intencao_interpreter.py` (ou domínio) |
| Resumo do pedido | `_gerar_resumo_pedido` | `domain/pedido_service.py` + formatter |
| Finalização via checkout | `_salvar_pedido_via_checkout` | `infrastructure/http_checkout_gateway.py` |
| Persistência local do pedido | `_salvar_pedido_no_banco` | `infrastructure/pedido_repository.py` |
| Cancelamento de pedido | `_cancelar_pedido` | `application/cancelar_pedido_*` |
| Fluxo de endereço | `_iniciar_fluxo_*`, `_processar_*endereco*` | `domain/endereco_domain_service.py` |
| Entrega/retirada | `_perguntar_entrega_ou_retirada`, `_processar_entrega_ou_retirada` | `application/definir_entrega_*` |
| Meios/processo de pagamento | `_buscar_meios_pagamento`, `_processar_pagamento` | `domain/pagamento_service.py` + repo |
| Estado de conversa | `_obter_estado_conversa`, `_salvar_estado_conversa` | `application/conversacao_service.py` |

---

## 🧭 Ordem sugerida de extração (para minimizar risco)

1. **Conversa/estado**: extrair repository + `ConversacaoService` (impacto baixo, reduz “efeito dominó”).
2. **Pagamento**: extrair `PagamentoDomainService` mantendo assinatura/retornos iguais.
3. **Endereço/entrega**: extrair `EnderecoDomainService` por etapas (primeiro “saved address”, depois Google).
4. **Pedido/checkout**: extrair gateway de checkout e depois regras de resumo/finalização.
5. **Preço/detecção**: extrair por último (mistura heurística + apresentação), mas vale muito para legibilidade.

**Heurística**: mover primeiro o que tem menos dependências e mais repetição; deixar IA/LLM e “detecção esperta” por último.
