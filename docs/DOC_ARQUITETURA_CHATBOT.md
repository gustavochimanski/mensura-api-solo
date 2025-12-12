# 📚 Documentação da Arquitetura do Chatbot

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura do Sistema](#arquitetura-do-sistema)
3. [Componentes Principais](#componentes-principais)
4. [Fluxo de Dados](#fluxo-de-dados)
5. [Banco de Dados](#banco-de-dados)
6. [Integrações Externas](#integrações-externas)
7. [Estados da Conversa](#estados-da-conversa)
8. [APIs e Endpoints](#apis-e-endpoints)
9. [Segurança e Autenticação](#segurança-e-autenticação)
10. [Configuração e Deploy](#configuração-e-deploy)

---

## 🎯 Visão Geral

O sistema de Chatbot do Mensura é uma solução completa de atendimento conversacional integrada com WhatsApp Business API, que utiliza Inteligência Artificial (IA) para processar vendas, suporte ao cliente e notificações de pedidos.

### Características Principais

- **Vendas Conversacionais**: Fluxo completo de vendas via WhatsApp
- **IA Integrada**: Utiliza Groq API (LLaMA 3.1) e Ollama para processamento de linguagem natural
- **Multi-empresa**: Suporte a múltiplas empresas com isolamento de dados
- **Integração com Pedidos**: Conectado ao sistema de pedidos (cardápio, mesas, balcão)
- **Gerenciamento de Endereços**: Integração com Google Maps para busca e validação de endereços
- **Notificações**: Sistema de notificações de pedidos via WhatsApp

---

## 🏗️ Arquitetura do Sistema

### Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        WhatsApp Business API                     │
│                         (Meta/Facebook)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Webhook
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Router Layer                         │
│              app/api/chatbot/router/router.py                    │
│  - /api/chatbot/webhook (recebe mensagens WhatsApp)            │
│  - /api/chatbot/chat (chat genérico com IA)                     │
│  - /api/chatbot/prompts (gerenciamento de prompts)             │
│  - /api/chatbot/conversations (gerenciamento de conversas)      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Core Business Logic Layer                     │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │  GroqSalesHandler    │  │  LLMSalesHandler      │            │
│  │  (Vendas com Groq)   │  │  (Vendas com Ollama)  │            │
│  └──────────────────────┘  └──────────────────────┘            │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │  SalesAssistant      │  │  SalesHandler        │            │
│  │  (Lógica de vendas)   │  │  (Gerenciamento)     │            │
│  └──────────────────────┘  └──────────────────────┘            │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │  AddressService      │  │  OrderNotification   │            │
│  │  (Endereços)         │  │  (Notificações)       │            │
│  └──────────────────────┘  └──────────────────────┘            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Access Layer                             │
│              app/api/chatbot/core/database.py                     │
│  - Gerenciamento de conversas                                   │
│  - Gerenciamento de mensagens                                   │
│  - Gerenciamento de prompts                                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                           │
│                                                                  │
│  Schema: chatbot                                                │
│  - prompts                                                      │
│  - conversations                                                │
│  - messages                                                     │
│                                                                  │
│  Schema: cadastros                                              │
│  - clientes                                                     │
│  - enderecos                                                    │
│                                                                  │
│  Schema: catalogo                                                │
│  - produtos                                                     │
│  - categorias                                                   │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                             │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Groq API    │  │  Google Maps  │  │  Ollama      │         │
│  │  (LLaMA 3.1) │  │  (Geocoding)  │  │  (Local LLM) │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Componentes Principais

### 1. Router Layer (`router/router.py`)

**Responsabilidade**: Recebe requisições HTTP e roteia para os handlers apropriados.

**Principais Endpoints**:
- `POST /api/chatbot/webhook`: Webhook do WhatsApp para receber mensagens
- `POST /api/chatbot/chat`: Endpoint genérico de chat com IA
- `GET /api/chatbot/health`: Health check do sistema
- `GET/POST /api/chatbot/prompts/*`: CRUD de prompts
- `GET/POST /api/chatbot/conversations/*`: CRUD de conversas

**Fluxo Principal**:
```python
# Quando recebe mensagem via WhatsApp
@router.post("/webhook")
async def webhook_handler():
    1. Extrai mensagem do payload do WhatsApp
    2. Identifica usuário (telefone)
    3. Busca ou cria conversa
    4. Processa mensagem com GroqSalesHandler
    5. Envia resposta via WhatsApp
```

### 2. GroqSalesHandler (`core/groq_sales_handler.py`)

**Responsabilidade**: Handler principal de vendas usando Groq API (LLaMA 3.1).

**Características**:
- Processamento de linguagem natural com Function Calling
- Gerenciamento de estado da conversa
- Integração com banco de dados para buscar produtos
- Fluxo completo de vendas: busca → seleção → endereço → pagamento → checkout

**Funções da IA (Function Calling)**:
- `adicionar_produto`: Adiciona produto ao carrinho
- `finalizar_pedido`: Inicia processo de finalização
- `ver_cardapio`: Mostra cardápio completo
- `ver_carrinho`: Mostra itens do carrinho
- `remover_produto`: Remove item do carrinho
- `informar_sobre_produto`: Informa sobre produto específico
- `conversar`: Conversa casual/suporte

**Estados Gerenciados**:
- `STATE_WELCOME`: Boas-vindas
- `STATE_AGUARDANDO_PEDIDO`: Aguardando pedido do cliente
- `STATE_PERGUNTANDO_ENTREGA_RETIRADA`: Escolha entre entrega ou retirada
- `STATE_LISTANDO_ENDERECOS`: Listando endereços salvos
- `STATE_BUSCANDO_ENDERECO_GOOGLE`: Buscando endereço no Google Maps
- `STATE_COLETANDO_COMPLEMENTO`: Coletando complemento do endereço
- `STATE_COLETANDO_PAGAMENTO`: Coletando método de pagamento
- `STATE_CONFIRMANDO_PEDIDO`: Confirmando pedido final

### 3. AddressService (`core/address_service.py`)

**Responsabilidade**: Gerenciamento de endereços do cliente.

**Funcionalidades**:
- Busca cliente por telefone
- Lista endereços salvos do cliente
- Busca endereços no Google Maps
- Valida e cadastra novos endereços
- Normalização de endereços

**Integração**:
- Google Maps API para geocoding
- Tabela `cadastros.enderecos` para persistência
- Tabela `cadastros.clientes` para identificação

### 4. OrderNotification (`core/notifications.py`)

**Responsabilidade**: Envio de notificações de pedidos via WhatsApp.

**Tipos de Notificação**:
- **Delivery/Cardápio**: Pedidos com entrega
- **Mesa**: Pedidos para consumo no local
- **Balcão**: Pedidos para retirada

**Formato das Mensagens**:
- Mensagens formatadas com emojis
- Informações do pedido (itens, total, endereço)
- Tempo estimado de entrega/preparo
- QR Code PIX (quando aplicável)

### 5. Database Module (`core/database.py`)

**Responsabilidade**: Acesso ao banco de dados PostgreSQL.

**Schema**: `chatbot`

**Tabelas**:
- `prompts`: Prompts do sistema (system prompts)
- `conversations`: Conversas dos usuários
- `messages`: Mensagens das conversas

**Funcionalidades**:
- CRUD de prompts
- CRUD de conversas
- CRUD de mensagens
- Estatísticas do sistema
- Seed de prompts padrão

### 6. SalesPrompts (`core/sales_prompts.py`)

**Responsabilidade**: Definição de prompts do sistema para vendas.

**Conteúdo**:
- System prompts para diferentes contextos
- Mensagens de boas-vindas
- Mensagens de erro
- Templates de resposta

### 7. ConfigWhatsApp (`core/config_whatsapp.py`)

**Responsabilidade**: Configuração e gerenciamento da integração com WhatsApp Business API.

**Configurações**:
- Access Token
- Phone Number ID
- Business Account ID
- API Version

---

## 🔄 Fluxo de Dados

### Fluxo de Mensagem Recebida (WhatsApp → Resposta)

```
1. WhatsApp Business API recebe mensagem do cliente
   ↓
2. Webhook envia POST para /api/chatbot/webhook
   ↓
3. Router extrai dados da mensagem (telefone, texto)
   ↓
4. Busca ou cria conversa no banco de dados
   ↓
5. GroqSalesHandler.processar_mensagem()
   ↓
6. IA (Groq) interpreta intenção usando Function Calling
   ↓
7. Handler executa ação baseada na intenção:
   - Busca produtos no banco
   - Adiciona ao carrinho
   - Processa endereço
   - Finaliza pedido
   ↓
8. Gera resposta usando IA ou templates
   ↓
9. Salva mensagem no banco de dados
   ↓
10. Envia resposta via WhatsApp Business API
```

### Fluxo de Venda Completo

```
1. Cliente: "Oi"
   → Bot: Mensagem de boas-vindas + promoções
   ↓
2. Cliente: "Quero pizza"
   → Bot: Busca produtos → Lista opções
   ↓
3. Cliente: "1" (seleciona produto)
   → Bot: "Quantos você quer?"
   ↓
4. Cliente: "2"
   → Bot: Adiciona ao carrinho → "Quer mais alguma coisa?"
   ↓
5. Cliente: "Pode fechar"
   → Bot: "É entrega ou retirada?"
   ↓
6. Cliente: "Entrega"
   → Bot: Lista endereços salvos ou busca no Google Maps
   ↓
7. Cliente: Seleciona/fornece endereço
   → Bot: Coleta complemento (se necessário)
   ↓
8. Bot: "Como vai ser o pagamento? 1-PIX 2-Dinheiro 3-Cartão"
   ↓
9. Cliente: "1" (PIX)
   → Bot: Chama /checkout/preview → Mostra resumo
   ↓
10. Cliente: "OK"
    → Bot: Chama /checkout/finalizar → Cria pedido
    → Bot: Envia notificação com QR Code PIX
```

---

## 🗄️ Banco de Dados

### Schema: `chatbot`

#### Tabela: `prompts`

Armazena os prompts do sistema (system prompts) para diferentes contextos.

```sql
CREATE TABLE chatbot.prompts (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    empresa_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Campos**:
- `key`: Chave única do prompt (ex: "default", "sales", "support")
- `name`: Nome descritivo do prompt
- `content`: Conteúdo do system prompt
- `is_default`: Se é um prompt padrão (não pode ser deletado)
- `empresa_id`: ID da empresa (NULL = global)

#### Tabela: `conversations`

Armazena as conversas dos usuários.

```sql
CREATE TABLE chatbot.conversations (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    prompt_key VARCHAR(100),
    model VARCHAR(100) NOT NULL,
    empresa_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_key) REFERENCES chatbot.prompts(key)
);
```

**Campos**:
- `session_id`: ID único da sessão
- `user_id`: ID do usuário (geralmente telefone do WhatsApp)
- `prompt_key`: Chave do prompt usado
- `model`: Modelo de IA usado (ex: "llama3.1:8b", "llm-sales")
- `empresa_id`: ID da empresa

#### Tabela: `messages`

Armazena as mensagens das conversas.

```sql
CREATE TABLE chatbot.messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES chatbot.conversations(id) ON DELETE CASCADE
);
```

**Campos**:
- `conversation_id`: ID da conversa
- `role`: Papel da mensagem ("user" ou "assistant")
- `content`: Conteúdo da mensagem

**Índices**:
- `idx_conversations_session`: Índice em `session_id`
- `idx_conversations_user`: Índice em `user_id`
- `idx_conversations_empresa`: Índice em `empresa_id`
- `idx_messages_conversation`: Índice em `conversation_id`

### Integração com Outros Schemas

O chatbot integra com:

- **`cadastros.clientes`**: Identificação de clientes por telefone
- **`cadastros.enderecos`**: Endereços dos clientes
- **`catalogo.produtos`**: Busca de produtos para vendas
- **`pedidos.*`**: Criação e gerenciamento de pedidos

---

## 🔌 Integrações Externas

### 1. WhatsApp Business API (Meta)

**Propósito**: Receber e enviar mensagens via WhatsApp.

**Configuração**:
- Access Token: Token de autenticação
- Phone Number ID: ID do número de telefone
- Business Account ID: ID da conta de negócios
- API Version: Versão da API (padrão: v22.0)

**Endpoints Utilizados**:
- `POST /v{version}/{phone_number_id}/messages`: Envio de mensagens

**Formato de Mensagem**:
```json
{
    "messaging_product": "whatsapp",
    "to": "5511999999999",
    "type": "text",
    "text": {
        "preview_url": false,
        "body": "Mensagem aqui"
    }
}
```

### 2. Groq API

**Propósito**: Processamento de linguagem natural com LLaMA 3.1.

**Configuração**:
- API Key: Chave da API (variável de ambiente `GROQ_API_KEY`)
- Model: `llama-3.1-8b-instant`
- Endpoint: `https://api.groq.com/openai/v1/chat/completions`

**Funcionalidades**:
- Function Calling para interpretação de intenções
- Geração de respostas conversacionais
- Processamento de contexto da conversa

**Exemplo de Requisição**:
```json
{
    "model": "llama-3.1-8b-instant",
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ],
    "tools": [...],
    "tool_choice": "auto"
}
```

### 3. Google Maps API

**Propósito**: Busca e validação de endereços.

**Funcionalidades**:
- Geocoding: Conversão de endereço em coordenadas
- Place Search: Busca de lugares
- Address Validation: Validação de endereços

**Integração**: Via `app/api/localizacao/adapters/google_maps_adapter.py`

### 4. Ollama (Opcional)

**Propósito**: LLM local como alternativa ao Groq.

**Configuração**:
- URL: `http://localhost:11434/api/chat`
- Model: `llama3.1:8b`

**Uso**: Para desenvolvimento local ou quando Groq não está disponível.

---

## 📊 Estados da Conversa

O sistema gerencia estados da conversa para controlar o fluxo de vendas:

### Estados Principais

1. **`STATE_WELCOME`**
   - Estado inicial
   - Envia mensagem de boas-vindas
   - Transição: → `STATE_AGUARDANDO_PEDIDO`

2. **`STATE_AGUARDANDO_PEDIDO`**
   - Aguardando cliente fazer pedido
   - Processa busca de produtos
   - Transição: → `STATE_AGUARDANDO_QUANTIDADE` ou `STATE_PERGUNTANDO_ENTREGA_RETIRADA`

3. **`STATE_AGUARDANDO_QUANTIDADE`**
   - Aguardando quantidade do produto
   - Transição: → `STATE_AGUARDANDO_MAIS_ITENS`

4. **`STATE_AGUARDANDO_MAIS_ITENS`**
   - Aguardando mais itens ou finalização
   - Transição: → `STATE_PERGUNTANDO_ENTREGA_RETIRADA` ou `STATE_AGUARDANDO_PEDIDO`

5. **`STATE_PERGUNTANDO_ENTREGA_RETIRADA`**
   - Perguntando se é entrega ou retirada
   - Transição: → `STATE_LISTANDO_ENDERECOS` (entrega) ou `STATE_COLETANDO_PAGAMENTO` (retirada)

6. **`STATE_LISTANDO_ENDERECOS`**
   - Listando endereços salvos do cliente
   - Transição: → `STATE_BUSCANDO_ENDERECO_GOOGLE` ou `STATE_COLETANDO_COMPLEMENTO`

7. **`STATE_BUSCANDO_ENDERECO_GOOGLE`**
   - Buscando endereço no Google Maps
   - Transição: → `STATE_SELECIONANDO_ENDERECO_GOOGLE`

8. **`STATE_SELECIONANDO_ENDERECO_GOOGLE`**
   - Cliente seleciona endereço da busca
   - Transição: → `STATE_COLETANDO_COMPLEMENTO`

9. **`STATE_COLETANDO_COMPLEMENTO`**
   - Coletando complemento do endereço
   - Transição: → `STATE_COLETANDO_PAGAMENTO`

10. **`STATE_COLETANDO_PAGAMENTO`**
    - Coletando método de pagamento
    - Transição: → `STATE_CONFIRMANDO_PEDIDO`

11. **`STATE_CONFIRMANDO_PEDIDO`**
    - Mostrando preview e aguardando confirmação
    - Transição: → `STATE_WELCOME` (após confirmação)

### Persistência de Estado

**Atual**: Estado armazenado em memória (dicionário Python)

**Recomendado para Produção**: 
- Redis para cache rápido
- Banco de dados para persistência duradoura

---

## 🌐 APIs e Endpoints

### Endpoints do Chatbot

#### `POST /api/chatbot/webhook`
Recebe webhooks do WhatsApp Business API.

**Request Body** (formato WhatsApp):
```json
{
    "entry": [{
        "changes": [{
            "value": {
                "messages": [{
                    "from": "5511999999999",
                    "text": {
                        "body": "Mensagem do cliente"
                    }
                }]
            }
        }]
    }]
}
```

**Response**:
```json
{
    "status": "success"
}
```

#### `POST /api/chatbot/chat`
Endpoint genérico de chat com IA.

**Request**:
```json
{
    "messages": [
        {"role": "user", "content": "Olá"}
    ],
    "model": "llama3.1:8b",
    "system_prompt": "Você é um assistente..."
}
```

**Response**:
```json
{
    "response": "Olá! Como posso ajudar?",
    "model": "llama3.1:8b"
}
```

#### `GET /api/chatbot/health`
Verifica saúde do sistema e disponibilidade do Ollama.

**Response**:
```json
{
    "ollama": "online",
    "models_disponiveis": ["llama3.1:8b", ...]
}
```

#### `GET /api/chatbot/prompts`
Lista todos os prompts.

#### `POST /api/chatbot/prompts`
Cria um novo prompt.

#### `GET /api/chatbot/conversations`
Lista conversas de um usuário.

#### `POST /api/chatbot/conversations`
Cria uma nova conversa.

#### `GET /api/chatbot/conversations/{id}/messages`
Lista mensagens de uma conversa.

### Integração com Endpoints de Pedidos

O chatbot integra com endpoints do módulo de pedidos:

- `POST /api/cardapio/client/checkout/preview`: Preview do pedido
- `POST /api/cardapio/client/checkout/finalizar`: Finalização do pedido

---

## 🔐 Segurança e Autenticação

### Autenticação de Clientes

**Atual**: Identificação por telefone do WhatsApp

**Recomendações**:
- Implementar autenticação via token para endpoints de checkout
- Validar telefone antes de criar pedidos
- Rate limiting para prevenir spam

### Segurança de Dados

- **Isolamento por Empresa**: Dados isolados por `empresa_id`
- **Validação de Entrada**: Schemas Pydantic para validação
- **SQL Injection**: Uso de SQL parametrizado (SQLAlchemy text())
- **Secrets**: Configurações sensíveis via variáveis de ambiente

### Variáveis de Ambiente Necessárias

```bash
GROQ_API_KEY=seu_groq_api_key
WHATSAPP_ACCESS_TOKEN=seu_whatsapp_token
WHATSAPP_PHONE_NUMBER_ID=seu_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=seu_business_account_id
GOOGLE_MAPS_API_KEY=seu_google_maps_key
```

---

## ⚙️ Configuração e Deploy

### Pré-requisitos

- Python 3.10+
- PostgreSQL 12+
- FastAPI
- Acesso à Groq API
- Conta WhatsApp Business API

### Instalação

1. **Instalar dependências**:
```bash
pip install -r requirements.txt
```

2. **Configurar variáveis de ambiente**:
```bash
export GROQ_API_KEY="..."
export WHATSAPP_ACCESS_TOKEN="..."
```

3. **Inicializar banco de dados**:
```python
from app.api.chatbot.core.database import init_database
from app.database.db_connection import get_db

db = next(get_db())
init_database(db)
```

4. **Configurar webhook do WhatsApp**:
   - URL: `https://seu-dominio.com/api/chatbot/webhook`
   - Método: POST
   - Verificar token de verificação

### Estrutura de Arquivos

```
app/api/chatbot/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── address_service.py          # Serviço de endereços
│   ├── config_whatsapp.py          # Config WhatsApp
│   ├── database.py                  # Acesso ao banco
│   ├── groq_sales_handler.py        # Handler principal (Groq)
│   ├── llm_sales_handler.py         # Handler alternativo (Ollama)
│   ├── llm_tools.py                 # Ferramentas LLM
│   ├── ngrok_manager.py             # Gerenciamento Ngrok (dev)
│   ├── notifications.py             # Notificações
│   ├── sales_assistant.py           # Assistente de vendas
│   ├── sales_handler.py             # Handler de vendas
│   └── sales_prompts.py             # Prompts do sistema
├── models/
│   └── __init__.py
├── router/
│   ├── __init__.py
│   └── router.py                    # Rotas principais
├── schemas/
│   ├── __init__.py
│   └── schemas.py                   # Schemas Pydantic
└── SALES_INTEGRATION_README.md      # README de integração
```

### Monitoramento

**Logs**:
- Mensagens processadas
- Erros de API
- Estados da conversa
- Tempo de resposta

**Métricas Recomendadas**:
- Número de conversas ativas
- Taxa de conversão (mensagens → pedidos)
- Tempo médio de resposta
- Erros de integração

---

## 🚀 Melhorias Futuras

### Curto Prazo
- [ ] Implementar Redis para estado de conversa
- [ ] Adicionar autenticação de clientes
- [ ] Melhorar busca de produtos (fuzzy search)
- [ ] Adicionar suporte a adicionais/combos

### Médio Prazo
- [ ] Histórico de pedidos do cliente
- [ ] Sistema de cupons de desconto
- [ ] Tracking de entrega em tempo real
- [ ] Análise de sentimento das mensagens

### Longo Prazo
- [ ] Suporte a múltiplos idiomas
- [ ] Integração com outros canais (Telegram, Instagram)
- [ ] Dashboard de analytics
- [ ] A/B testing de prompts

---

## 📝 Notas Técnicas

### Performance

- **Cache**: Estado de conversa em memória (migrar para Redis)
- **Async**: Uso de `async/await` para operações I/O
- **Connection Pooling**: SQLAlchemy gerencia pool de conexões

### Escalabilidade

- **Stateless**: Handlers são stateless (exceto estado em memória)
- **Horizontal Scaling**: Pode escalar horizontalmente com Redis compartilhado
- **Rate Limiting**: Implementar rate limiting por usuário

### Troubleshooting

**Problema**: Produtos não são encontrados
- Verificar se produtos estão ativos no banco
- Confirmar `empresa_id` correto
- Verificar permissões de acesso ao banco

**Problema**: Preview retorna erro
- Testar endpoint `/checkout/preview` diretamente
- Verificar schemas Pydantic
- Confirmar autenticação do cliente

**Problema**: Estado da conversa não persiste
- Implementar Redis ou banco de dados
- Verificar TTL do cache

---

## 📚 Referências

- [WhatsApp Business API Documentation](https://developers.facebook.com/docs/whatsapp)
- [Groq API Documentation](https://console.groq.com/docs)
- [Ollama Documentation](https://ollama.ai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

---

**Documentação criada em**: Dezembro 2024  
**Versão do Sistema**: 1.0  
**Mantido por**: Equipe Mensura

