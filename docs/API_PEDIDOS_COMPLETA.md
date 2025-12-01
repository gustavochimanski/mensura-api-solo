# API de Pedidos - Documentação Completa

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Estrutura de Dados](#estrutura-de-dados)
3. [Autenticação](#autenticação)
4. [Endpoints Admin](#endpoints-admin)
5. [Endpoints Client](#endpoints-client)
6. [Modelos de Dados](#modelos-de-dados)
7. [Status e Tipos](#status-e-tipos)
8. [Exemplos Completos](#exemplos-completos)

---

## 🎯 Visão Geral

A API de Pedidos unificada centraliza todos os tipos de pedidos (DELIVERY, MESA, BALCAO) em uma única estrutura de dados e conjunto de endpoints.

### Características Principais

- ✅ **Modelo Unificado**: Todos os pedidos na tabela `pedidos.pedidos` com campo `tipo_pedido`
- ✅ **Histórico Unificado**: Histórico de alterações na tabela `pedidos.pedidos_historico`
- ✅ **Itens Unificados**: Suporta produtos, receitas e combos na mesma tabela
- ✅ **Endpoints Específicos**: Rotas separadas para admin e client
- ✅ **Autenticação Diferente**: Admin usa token de usuário, Client usa token de cliente

### Tipos de Pedido

1. **DELIVERY**: Pedidos de entrega (requer endereço)
2. **MESA**: Pedidos de mesa (requer mesa)
3. **BALCAO**: Pedidos de balcão (opcional mesa)

---

## 🗄️ Estrutura de Dados

### Tabela: `pedidos.pedidos`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | INTEGER | ID único do pedido |
| `tipo_pedido` | ENUM | Tipo do pedido: DELIVERY, MESA, BALCAO |
| `empresa_id` | INTEGER | ID da empresa (FK) |
| `numero_pedido` | VARCHAR(20) | Número do pedido (único por empresa) |
| `status` | ENUM | Status do pedido (P, I, R, S, E, C, D, X, A) |
| `cliente_id` | INTEGER | ID do cliente (FK, nullable) |
| `mesa_id` | INTEGER | ID da mesa (FK, nullable - para MESA e BALCAO) |
| `endereco_id` | INTEGER | ID do endereço (FK, nullable - para DELIVERY) |
| `entregador_id` | INTEGER | ID do entregador (FK, nullable - para DELIVERY) |
| `meio_pagamento_id` | INTEGER | ID do meio de pagamento (FK, nullable) |
| `cupom_id` | INTEGER | ID do cupom de desconto (FK, nullable) |
| `tipo_entrega` | ENUM | Tipo de entrega: DELIVERY, RETIRADA (apenas DELIVERY) |
| `origem` | ENUM | Origem do pedido: WEB, APP, BALCAO (apenas DELIVERY) |
| `subtotal` | NUMERIC(18,2) | Subtotal dos itens |
| `desconto` | NUMERIC(18,2) | Valor do desconto |
| `taxa_entrega` | NUMERIC(18,2) | Taxa de entrega (apenas DELIVERY) |
| `taxa_servico` | NUMERIC(18,2) | Taxa de serviço |
| `valor_total` | NUMERIC(18,2) | Valor total do pedido |
| `troco_para` | NUMERIC(18,2) | Valor do troco (nullable) |
| `observacoes` | VARCHAR(500) | Observações (MESA e BALCAO) |
| `observacao_geral` | VARCHAR(255) | Observação geral (DELIVERY) |
| `num_pessoas` | INTEGER | Número de pessoas (MESA) |
| `previsao_entrega` | TIMESTAMP | Previsão de entrega (DELIVERY) |
| `distancia_km` | NUMERIC(10,3) | Distância em km (DELIVERY) |
| `endereco_snapshot` | JSONB | Snapshot do endereço (DELIVERY) |
| `endereco_geo` | GEOGRAPHY | Coordenadas geográficas (DELIVERY) |
| `created_at` | TIMESTAMP | Data de criação |
| `updated_at` | TIMESTAMP | Data de atualização |

### Tabela: `pedidos.pedidos_historico`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | INTEGER | ID único do registro |
| `pedido_id` | INTEGER | ID do pedido (FK) |
| `tipo_pedido` | ENUM | Tipo do pedido: DELIVERY, MESA ou BALCAO |
| `tipo_operacao` | ENUM | Tipo de operação: PEDIDO_CRIADO, STATUS_ALTERADO, ITEM_ADICIONADO, etc. (nullable) |
| `status_anterior` | ENUM | Status anterior (nullable) |
| `status_novo` | ENUM | Status novo (nullable) |
| `descricao` | TEXT | Descrição da operação (nullable) |
| `motivo` | TEXT | Motivo da mudança (nullable) |
| `observacoes` | TEXT | Observações adicionais (nullable) |
| `usuario_id` | INTEGER | ID do usuário (FK, nullable) |
| `cliente_id` | INTEGER | ID do cliente (FK, nullable) |
| `ip_origem` | VARCHAR(45) | IP de origem (nullable) |
| `user_agent` | VARCHAR(500) | User agent (nullable) |
| `created_at` | TIMESTAMP | Data do registro |

**Nota:** 
- A coluna `tipo_pedido` no histórico armazena o tipo do pedido: **DELIVERY, MESA ou BALCAO**
- A coluna `tipo_operacao` no histórico armazena o tipo de operação: **PEDIDO_CRIADO, STATUS_ALTERADO, ITEM_ADICIONADO, etc.**

---

## 🔐 Autenticação

### Admin Endpoints
```
Authorization: Bearer {admin_token}
```
Requer token de autenticação de administrador via `get_current_user`.

### Client Endpoints
```
Authorization: Bearer {client_token}
```
Requer token de cliente via `get_cliente_by_super_token`.

---

## 👨‍💼 Endpoints Admin

### Base URL
```
/api/pedidos/admin
```

---

### 1. Listar Pedidos (Kanban)

Agrupa todos os pedidos por tipo para visualização no Kanban.

**Endpoint:**
```
GET /api/pedidos/admin/kanban
```

**Query Parameters:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `date_filter` | date | ✅ Sim | Data no formato YYYY-MM-DD |
| `empresa_id` | int | ✅ Sim | ID da empresa (deve ser > 0) |
| `limit` | int | ❌ Não | Limite de pedidos por categoria (padrão: 500, máx: 1000) |

**Request:**
```http
GET /api/pedidos/admin/kanban?date_filter=2024-01-15&empresa_id=1&limit=500
Authorization: Bearer {admin_token}
```

**Response (200 OK):**
```json
{
  "delivery": [
    {
      "id": 123,
      "tipo_pedido": "DELIVERY",
      "status": "I",
      "numero_pedido": "DV-000123",
      "cliente": {
        "id": 45,
        "nome": "João Silva",
        "telefone": "11999999999"
      },
      "valor_total": 45.90,
      "data_criacao": "2024-01-15T10:30:00",
      "endereco": "Rua Exemplo, 123 - São Paulo/SP",
      "entregador": {
        "id": 5,
        "nome": "Carlos"
      },
      "meio_pagamento": {
        "id": 1,
        "nome": "Dinheiro",
        "tipo": "DINHEIRO"
      }
    }
  ],
  "balcao": [
    {
      "id": 456,
      "tipo_pedido": "BALCAO",
      "status": "I",
      "numero_pedido": "BAL-000456",
      "valor_total": 32.50,
      "mesa_id": 10,
      "mesa_numero": "M10"
    }
  ],
  "mesas": [
    {
      "id": 789,
      "tipo_pedido": "MESA",
      "status": "I",
      "numero_pedido": "M12-001",
      "valor_total": 78.00,
      "mesa_id": 12,
      "mesa_numero": "M12"
    }
  ]
}
```

---

### 2. Buscar Pedido por ID

Busca um pedido específico com todas as informações completas.

**Endpoint:**
```
GET /api/pedidos/admin/{pedido_id}
```

**Path Parameters:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | int | ✅ Sim | ID do pedido (deve ser > 0) |

**Request:**
```http
GET /api/pedidos/admin/123
Authorization: Bearer {admin_token}
```

**Response (200 OK):**
```json
{
  "id": 123,
  "tipo_pedido": "DELIVERY",
  "numero_pedido": "DV-000123",
  "status": "I",
  "empresa_id": 1,
  "cliente_id": 45,
  "cliente": {
    "id": 45,
    "nome": "João Silva",
    "telefone": "11999999999"
  },
  "endereco_id": 10,
  "endereco": {
    "id": 10,
    "logradouro": "Rua Exemplo",
    "numero": "123",
    "bairro": "Centro",
    "cidade": "São Paulo",
    "estado": "SP",
    "cep": "01234567"
  },
  "itens": [
    {
      "id": 1,
      "produto_cod_barras": "7891234567890",
      "receita_id": null,
      "combo_id": null,
      "quantidade": 2,
      "preco_unitario": 15.90,
      "preco_total": 31.80,
      "observacao": "Sem cebola",
      "produto_descricao_snapshot": "Hambúrguer Artesanal"
    }
  ],
  "subtotal": 47.30,
  "desconto": 0.00,
  "taxa_entrega": 5.00,
  "taxa_servico": 0.00,
  "valor_total": 52.30,
  "meio_pagamento_id": 1,
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:35:00"
}
```

---

### 3. Obter Histórico do Pedido

Obtém o histórico completo de alterações de um pedido.

**Endpoint:**
```
GET /api/pedidos/admin/{pedido_id}/historico
```

**Path Parameters:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | int | ✅ Sim | ID do pedido (deve ser > 0) |

**Request:**
```http
GET /api/pedidos/admin/123/historico
Authorization: Bearer {admin_token}
```

**Response (200 OK):**
```json
{
  "pedido_id": 123,
  "historicos": [
    {
      "id": 1,
      "pedido_id": 123,
      "status": "I",
      "status_anterior": "P",
      "status_novo": "I",
      "tipo_pedido": "STATUS_ALTERADO",
      "descricao": "Status atualizado para I",
      "motivo": "Pendente → Em impressão",
      "observacoes": null,
      "criado_em": "2024-01-15T10:35:00",
      "criado_por": "admin",
      "usuario_id": 1,
      "cliente_id": null,
      "ip_origem": "192.168.1.1",
      "user_agent": "Mozilla/5.0..."
    },
    {
      "id": 2,
      "pedido_id": 123,
      "status": "P",
      "status_anterior": null,
      "status_novo": "P",
      "tipo_pedido": "PEDIDO_CRIADO",
      "descricao": "Pedido criado",
      "motivo": "Pedido criado",
      "criado_em": "2024-01-15T10:30:00",
      "criado_por": null,
      "usuario_id": null
    }
  ]
}
```

**Nota:** 
- A coluna `tipo_pedido` no histórico armazena o tipo do pedido: **DELIVERY, MESA ou BALCAO**
- A coluna `tipo_operacao` no histórico armazena o tipo de operação: **PEDIDO_CRIADO, STATUS_ALTERADO, ITEM_ADICIONADO, etc.**

---

### 4. Atualizar Status do Pedido

Atualiza o status de um pedido.

**Endpoint:**
```
PUT /api/pedidos/admin/{pedido_id}/status
```

**Path Parameters:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | int | ✅ Sim | ID do pedido (deve ser > 0) |

**Query Parameters:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `novo_status` | enum | ✅ Sim | Novo status do pedido |

**Status Disponíveis:**
- `P` = PENDENTE
- `I` = EM IMPRESSÃO
- `R` = EM PREPARO
- `S` = SAIU PARA ENTREGA
- `E` = ENTREGUE
- `C` = CANCELADO
- `D` = EDITADO
- `X` = EM EDIÇÃO
- `A` = AGUARDANDO PAGAMENTO

**Request:**
```http
PUT /api/pedidos/admin/123/status?novo_status=R
Authorization: Bearer {admin_token}
```

**Response (200 OK):**
```json
{
  "id": 123,
  "status": "R",
  "numero_pedido": "DV-000123",
  "valor_total": 52.30
}
```

---

### 5. Vincular Entregador

Vincula ou desvincula um entregador a um pedido de delivery.

**Endpoint:**
```
PUT /api/pedidos/admin/{pedido_id}/entregador
```

**Path Parameters:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | int | ✅ Sim | ID do pedido (deve ser > 0) |

**Query Parameters:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `entregador_id` | int \| null | ❌ Não | ID do entregador (null para desvincular) |

**Request - Vincular:**
```http
PUT /api/pedidos/admin/123/entregador?entregador_id=5
Authorization: Bearer {admin_token}
```

**Request - Desvincular:**
```http
PUT /api/pedidos/admin/123/entregador?entregador_id=null
Authorization: Bearer {admin_token}
```

**Response (200 OK):**
```json
{
  "id": 123,
  "entregador_id": 5,
  "entregador": {
    "id": 5,
    "nome": "Carlos"
  }
}
```

---

### 6. Desvincular Entregador

Desvincula o entregador atual de um pedido.

**Endpoint:**
```
DELETE /api/pedidos/admin/{pedido_id}/entregador
```

**Path Parameters:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | int | ✅ Sim | ID do pedido (deve ser > 0) |

**Request:**
```http
DELETE /api/pedidos/admin/123/entregador
Authorization: Bearer {admin_token}
```

**Response (200 OK):**
```json
{
  "id": 123,
  "entregador_id": null
}
```

---

### 7. Endpoints Específicos por Tipo

#### 7.1. Pedidos Delivery

**Base URL:** `/api/pedidos/admin/delivery`

- `POST /` - Criar pedido de delivery
- `GET /` - Listar pedidos de delivery
- `GET /{pedido_id}` - Obter pedido de delivery
- `GET /cliente/{cliente_id}` - Listar pedidos por cliente
- `PUT /{pedido_id}` - Atualizar pedido de delivery
- `PUT /{pedido_id}/itens` - Atualizar itens
- `PUT /{pedido_id}/status` - Atualizar status
- `PUT /{pedido_id}/entregador` - Vincular entregador
- `DELETE /{pedido_id}` - Cancelar pedido
- `DELETE /{pedido_id}/entregador` - Desvincular entregador

#### 7.2. Pedidos Mesa

**Base URL:** `/api/pedidos/admin/mesa`

- `POST /` - Criar pedido de mesa
- `GET /` - Listar pedidos de mesa
- `GET /{pedido_id}` - Obter pedido de mesa
- `GET /mesa/{mesa_id}/finalizados` - Listar pedidos finalizados da mesa
- `GET /cliente/{cliente_id}` - Listar pedidos por cliente
- `PUT /{pedido_id}/adicionar-item` - Adicionar item
- `PUT /{pedido_id}/adicionar-produto-generico` - Adicionar produto genérico
- `PUT /{pedido_id}/observacoes` - Atualizar observações
- `PUT /{pedido_id}/status` - Atualizar status
- `PUT /{pedido_id}/fechar-conta` - Fechar conta
- `PUT /{pedido_id}/reabrir` - Reabrir pedido
- `DELETE /{pedido_id}/item/{item_id}` - Remover item
- `DELETE /{pedido_id}` - Cancelar pedido

---

## 👤 Endpoints Client

### Base URL
```
/api/pedidos/client
```

---

### 1. Preview do Checkout

Calcula o preview do checkout sem criar o pedido.

**Endpoint:**
```
POST /api/pedidos/client/checkout/preview
```

**Request Body:**
```json
{
  "tipo_pedido": "DELIVERY",
  "empresa_id": 1,
  "endereco_id": 10,
  "tipo_entrega": "DELIVERY",
  "origem": "APP",
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "7891234567890",
        "quantidade": 2,
        "observacao": "Sem cebola"
      }
    ]
  }
}
```

**Response (200 OK):**
```json
{
  "subtotal": 47.30,
  "taxa_entrega": 5.00,
  "taxa_servico": 0.00,
  "valor_total": 52.30,
  "desconto": 0.00,
  "distancia_km": 2.5,
  "empresa_id": 1,
  "tempo_entrega_minutos": 45.0
}
```

---

### 2. Finalizar Checkout

Cria o pedido no banco de dados.

**Endpoint:**
```
POST /api/pedidos/client/checkout
```

**Request Body:**
```json
{
  "tipo_pedido": "DELIVERY",
  "empresa_id": 1,
  "endereco_id": 10,
  "tipo_entrega": "DELIVERY",
  "origem": "APP",
  "meio_pagamento_id": 1,
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "7891234567890",
        "quantidade": 2,
        "observacao": "Sem cebola"
      }
    ]
  }
}
```

**Response (201 Created):**
```json
{
  "id": 123,
  "tipo_pedido": "DELIVERY",
  "numero_pedido": "DV-000123",
  "status": "I",
  "valor_total": 52.30,
  "itens": [...],
  "created_at": "2024-01-15T10:30:00"
}
```

---

### 3. Listar Pedidos do Cliente

Lista todos os pedidos do cliente (DELIVERY, MESA e BALCAO) mesclados.

**Endpoint:**
```
GET /api/pedidos/client/
```

**Query Parameters:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `skip` | int | ❌ Não | Número de registros para pular (padrão: 0) |
| `limit` | int | ❌ Não | Limite de registros (padrão: 50, máx: 200) |

**Request:**
```http
GET /api/pedidos/client/?skip=0&limit=50
Authorization: Bearer {client_token}
```

**Response (200 OK):**
```json
[
  {
    "tipo_pedido": "DELIVERY",
    "criado_em": "2024-01-15T10:30:00",
    "atualizado_em": "2024-01-15T10:35:00",
    "status_codigo": "I",
    "status_descricao": "Em impressão",
    "numero_pedido": "123",
    "valor_total": 52.30,
    "delivery": {
      "id": 123,
      "status": "I",
      "valor_total": 52.30
    },
    "mesa": null,
    "balcao": null
  }
]
```

---

### 4. Atualizar Itens do Pedido

Adiciona, atualiza ou remove itens de um pedido.

**Endpoint:**
```
PUT /api/pedidos/client/{pedido_id}/itens
```

**Path Parameters:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | int | ✅ Sim | ID do pedido |

**Request Body - Adicionar:**
```json
{
  "acao": "adicionar",
  "produto_cod_barras": "7891234567890",
  "quantidade": 1,
  "observacao": "Sem cebola"
}
```

**Request Body - Atualizar:**
```json
{
  "acao": "atualizar",
  "id": 1,
  "quantidade": 2,
  "observacao": "Com cebola"
}
```

**Request Body - Remover:**
```json
{
  "acao": "remover",
  "id": 1
}
```

**Response (200 OK):**
```json
{
  "id": 123,
  "status": "I",
  "valor_total": 68.20,
  "itens": [...]
}
```

---

### 5. Editar Pedido

Edita informações gerais do pedido.

**Endpoint:**
```
PUT /api/pedidos/client/{pedido_id}/editar
```

**Path Parameters:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | int | ✅ Sim | ID do pedido |

**Request Body:**
```json
{
  "meio_pagamento_id": 2,
  "endereco_id": 11,
  "cupom_id": 5,
  "observacao_geral": "Nova observação",
  "troco_para": 100.00
}
```

**Response (200 OK):**
```json
{
  "id": 123,
  "meio_pagamento_id": 2,
  "endereco_id": 11,
  "cupom_id": 5,
  "observacao_geral": "Nova observação",
  "troco_para": 100.00,
  "valor_total": 52.30
}
```

---

## 📊 Modelos de Dados

### Tipo de Pedido (tipo_pedido)

```python
class TipoPedido(enum.Enum):
    DELIVERY = "DELIVERY"
    MESA = "MESA"
    BALCAO = "BALCAO"
```

### Status do Pedido

```python
class StatusPedido(enum.Enum):
    PENDENTE = "P"
    IMPRESSAO = "I"
    PREPARANDO = "R"
    SAIU_PARA_ENTREGA = "S"
    ENTREGUE = "E"
    CANCELADO = "C"
    EDITADO = "D"
    EM_EDICAO = "X"
    AGUARDANDO_PAGAMENTO = "A"
```

### Tipo de Operação (tipo_operacao no histórico)

```python
class TipoOperacaoPedido(enum.Enum):
    PEDIDO_CRIADO = "PEDIDO_CRIADO"
    STATUS_ALTERADO = "STATUS_ALTERADO"
    ITEM_ADICIONADO = "ITEM_ADICIONADO"
    ITEM_REMOVIDO = "ITEM_REMOVIDO"
    PEDIDO_CONFIRMADO = "PEDIDO_CONFIRMADO"
    PEDIDO_CANCELADO = "PEDIDO_CANCELADO"
    PEDIDO_FECHADO = "PEDIDO_FECHADO"
    PEDIDO_REABERTO = "PEDIDO_REABERTO"
    CLIENTE_ASSOCIADO = "CLIENTE_ASSOCIADO"
    CLIENTE_DESASSOCIADO = "CLIENTE_DESASSOCIADO"
    MESA_ASSOCIADA = "MESA_ASSOCIADA"
    MESA_DESASSOCIADA = "MESA_DESASSOCIADA"
    ENTREGADOR_ASSOCIADO = "ENTREGADOR_ASSOCIADO"
    ENTREGADOR_DESASSOCIADO = "ENTREGADOR_DESASSOCIADO"
    ENDERECO_ALTERADO = "ENDERECO_ALTERADO"
    PAGAMENTO_REALIZADO = "PAGAMENTO_REALIZADO"
    PAGAMENTO_CANCELADO = "PAGAMENTO_CANCELADO"
```

**Importante:** Na tabela `pedidos.pedidos_historico`, a coluna `tipo_pedido` armazena o tipo de operação realizada, não o tipo do pedido.

---

## ⚠️ Validações Importantes

### DELIVERY
- ✅ Requer: `empresa_id`, `endereco_id`, `tipo_entrega`, `origem`
- ✅ Opcional: `cliente_id`, `cupom_id`, `observacao_geral`

### MESA
- ✅ Requer: `empresa_id`, `mesa_id`
- ✅ Opcional: `cliente_id`, `num_pessoas`, `observacoes`

### BALCAO
- ✅ Requer: `empresa_id`
- ✅ Opcional: `mesa_id`, `cliente_id`, `observacoes`

### Histórico
- ✅ O campo `tipo_pedido` na tabela de histórico armazena: **DELIVERY, MESA ou BALCAO** (tipo do pedido)
- ✅ O campo `tipo_operacao` na tabela de histórico armazena: **PEDIDO_CRIADO, STATUS_ALTERADO, ITEM_ADICIONADO, etc.** (tipo de operação)
- ✅ `tipo_operacao` pode ser NULL para histórico simples (apenas mudança de status)
- ✅ `tipo_operacao` preenchido para histórico detalhado (com tipo de operação)

---

## 📝 Notas Finais

1. **Nomenclatura:** 
   - A coluna `tipo_pedido` no histórico armazena: **DELIVERY, MESA ou BALCAO** (tipo do pedido)
   - A coluna `tipo_operacao` no histórico armazena: **PEDIDO_CRIADO, STATUS_ALTERADO, ITEM_ADICIONADO, etc.** (tipo de operação)
2. **Compatibilidade:** A API mantém compatibilidade com histórico simples (status) e detalhado (tipo_operacao).
3. **Validações:** Todos os endpoints validam se o pedido pertence ao cliente/empresa correta.
4. **Permissões:** Clientes não podem alterar status diretamente; apenas admin pode.

---

## 🔗 Documentação Relacionada

- [API de Pedidos - Admin (Detalhado)](./API_PEDIDOS_UNIFICADOS_ADMIN.md)
- [API de Pedidos - Client (Detalhado)](./API_PEDIDOS_UNIFICADOS_CLIENT.md)
- [Resumo da Estrutura](./RESUMO_ESTRUTURA_PEDIDOS.md)

