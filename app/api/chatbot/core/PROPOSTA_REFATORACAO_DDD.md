# Proposta de Refatoração: Divisão do `groq_sales_handler.py` seguindo DDD

## 📊 Situação Atual

- **Arquivo**: `groq_sales_handler.py` (~7882 linhas)
- **Classe**: `GroqSalesHandler` com ~99 métodos
- **Problema**: Arquivo muito grande, difícil de manter e testar

## 🎯 Objetivo

Dividir o arquivo em múltiplos módulos seguindo **Domain-Driven Design (DDD)**, separando responsabilidades e facilitando manutenção.

## 🏗️ Estrutura Proposta

### 1. **Domain Services** (Lógica de Negócio)

#### `domain/produto_service.py`
**Responsabilidade**: Busca, normalização e manipulação de produtos

**Métodos a mover**:
- `_buscar_produto_por_termo()`
- `_buscar_todos_produtos()`
- `_buscar_produtos()`
- `_buscar_produtos_inteligente()`
- `_normalizar_termo_busca()`
- `_corrigir_termo_busca()`
- `_expandir_sinonimos()`
- `_resolver_produto_para_preco()`
- `_detectar_produto_na_mensagem()`
- `_buscar_promocoes()`

**Dependências**:
- `ProdutoAdapter`
- `ComboAdapter`
- Banco de dados

---

#### `domain/carrinho_service.py`
**Responsabilidade**: Operações de carrinho (adicionar, remover, formatar)

**Métodos a mover**:
- `_adicionar_ao_carrinho()`
- `_remover_do_carrinho()`
- `_personalizar_item_carrinho()`
- `_formatar_carrinho()`
- `_verificar_carrinho_aberto()`
- `_formatar_mensagem_carrinho_aberto()`
- `_carrinho_response_para_lista()`
- `_sincronizar_carrinho_dados()`
- `_montar_item_carrinho_request()`
- `_converter_contexto_para_carrinho()`
- `_get_carrinho_service()`
- `_obter_carrinho_db()`

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
- `_normalizar_mensagem()`
- `_extrair_quantidade()`
- `_extrair_quantidade_pergunta()`
- `_extrair_itens_pergunta_preco()`
- `_extrair_itens_pedido()`
- `_extrair_numero()`
- `_extrair_numero_natural()`

**Dependências**:
- Nenhuma (funções puras)

---

#### `utils/mensagem_formatters.py`
**Responsabilidade**: Formatação de mensagens para o usuário

**Métodos a mover**:
- `_gerar_mensagem_boas_vindas()`
- `_gerar_mensagem_boas_vindas_conversacional()`
- `_gerar_lista_produtos()`
- `_gerar_resposta_preco_itens()`
- `_formatar_horarios_funcionamento()`
- `_formatar_localizacao_empresas()`
- `_buscar_empresas_ativas()`

**Dependências**:
- Dados do banco

---

#### `utils/config_loader.py`
**Responsabilidade**: Carregamento de configurações

**Métodos a mover**:
- `_load_chatbot_config()`
- `_get_chatbot_config()`
- `_obter_link_cardapio()`
- `_obter_mensagem_final_pedido()`

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
