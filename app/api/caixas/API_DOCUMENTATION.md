# Documentação da API de Caixas

## Visão Geral

A API de Caixas foi reestruturada em duas partes principais:

1. **CRUD de Caixas** (`/api/caixa/admin/caixas`): Gerenciamento de caixas cadastrados (nome, descrição, status ativo/inativo)
2. **Aberturas de Caixa** (`/api/caixa/admin/aberturas`): Gerenciamento de aberturas e fechamentos de caixas

---

## 1. CRUD de Caixas

### Base URL
```
/api/caixa/admin/caixas
```

### Endpoints

#### 1.1. Criar Caixa
```http
POST /api/caixa/admin/caixas/
```

**Body:**
```json
{
  "empresa_id": 1,
  "nome": "Caixa Principal",
  "descricao": "Caixa principal da loja",
  "ativo": true
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "empresa_id": 1,
  "nome": "Caixa Principal",
  "descricao": "Caixa principal da loja",
  "ativo": true,
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-01T10:00:00",
  "empresa_nome": "Minha Empresa"
}
```

#### 1.2. Listar Caixas
```http
GET /api/caixa/admin/caixas/?empresa_id=1&ativo=true&skip=0&limit=100
```

**Query Parameters:**
- `empresa_id` (opcional): Filtrar por empresa
- `ativo` (opcional): Filtrar por status ativo (true/false)
- `skip` (opcional, padrão: 0): Número de registros para pular
- `limit` (opcional, padrão: 100): Limite de registros

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "empresa_id": 1,
    "nome": "Caixa Principal",
    "descricao": "Caixa principal da loja",
    "ativo": true,
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T10:00:00",
    "empresa_nome": "Minha Empresa"
  }
]
```

#### 1.3. Buscar Caixa por ID
```http
GET /api/caixa/admin/caixas/{caixa_id}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "empresa_id": 1,
  "nome": "Caixa Principal",
  "descricao": "Caixa principal da loja",
  "ativo": true,
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-01T10:00:00",
  "empresa_nome": "Minha Empresa"
}
```

#### 1.4. Atualizar Caixa
```http
PUT /api/caixa/admin/caixas/{caixa_id}
```

**Body:**
```json
{
  "nome": "Caixa Principal Atualizado",
  "descricao": "Nova descrição",
  "ativo": true
}
```

**Response:** `200 OK` (mesmo formato do GET)

#### 1.5. Deletar Caixa (Soft Delete)
```http
DELETE /api/caixa/admin/caixas/{caixa_id}
```

**Response:** `204 No Content`

---

## 2. Aberturas de Caixa

### Base URL
```
/api/caixa/admin/aberturas
```

### Endpoints

#### 2.1. Abrir Caixa
```http
POST /api/caixa/admin/aberturas/abrir
```

**Body:**
```json
{
  "caixa_id": 1,
  "empresa_id": 1,
  "valor_inicial": 100.00,
  "data_hora_abertura": "2024-01-01T10:00:00",
  "observacoes_abertura": "Abertura do dia"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "caixa_id": 1,
  "empresa_id": 1,
  "usuario_id_abertura": 1,
  "usuario_id_fechamento": null,
  "valor_inicial": 100.00,
  "valor_final": null,
  "saldo_esperado": null,
  "saldo_real": null,
  "diferenca": null,
  "status": "ABERTO",
  "data_abertura": "2024-01-01T10:00:00",
  "data_fechamento": null,
  "data_hora_abertura": "2024-01-01T10:00:00",
  "data_hora_fechamento": null,
  "observacoes_abertura": "Abertura do dia",
  "observacoes_fechamento": null,
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-01T10:00:00",
  "caixa_nome": "Caixa Principal",
  "empresa_nome": "Minha Empresa",
  "usuario_abertura_nome": "João",
  "usuario_fechamento_nome": null
}
```

**Validações:**
- Não permite abrir uma nova abertura se já existir uma abertura aberta para o caixa
- O caixa deve estar ativo

#### 2.2. Fechar Caixa
```http
POST /api/caixa/admin/aberturas/{caixa_abertura_id}/fechar
```

**Body:**
```json
{
  "saldo_real": 150.00,
  "data_hora_fechamento": "2024-01-01T18:00:00",
  "observacoes_fechamento": "Fechamento do dia",
  "conferencias": [
    {
      "meio_pagamento_id": 1,
      "valor_conferido": 200.00,
      "observacoes": "Conferência OK"
    }
  ]
}
```

**Response:** `200 OK` (mesmo formato do abrir, mas com status FECHADO)

**Validações:**
- A abertura deve estar aberta
- `saldo_real` é obrigatório e >= 0
- `conferencias` é opcional

#### 2.3. Buscar Abertura por ID
```http
GET /api/caixa/admin/aberturas/{caixa_abertura_id}
```

**Response:** `200 OK` (mesmo formato do abrir)

#### 2.4. Buscar Abertura Aberta
```http
GET /api/caixa/admin/aberturas/aberto/{empresa_id}?caixa_id=1
```

**Query Parameters:**
- `caixa_id` (opcional): Filtrar por caixa específico

**Response:** `200 OK` (mesmo formato do abrir) ou `404 Not Found`

#### 2.5. Listar Aberturas
```http
GET /api/caixa/admin/aberturas/?empresa_id=1&caixa_id=1&status=ABERTO&data_inicio=2024-01-01&data_fim=2024-01-31&skip=0&limit=100
```

**Query Parameters:**
- `empresa_id` (opcional): Filtrar por empresa
- `caixa_id` (opcional): Filtrar por caixa
- `status` (opcional): Filtrar por status (ABERTO/FECHADO)
- `data_inicio` (opcional): Data início (YYYY-MM-DD)
- `data_fim` (opcional): Data fim (YYYY-MM-DD)
- `skip` (opcional, padrão: 0): Número de registros para pular
- `limit` (opcional, padrão: 100): Limite de registros

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "caixa_id": 1,
    "caixa_nome": "Caixa Principal",
    "empresa_id": 1,
    "empresa_nome": "Minha Empresa",
    "usuario_abertura_nome": "João",
    "valor_inicial": 100.00,
    "valor_final": null,
    "saldo_esperado": null,
    "saldo_real": null,
    "diferenca": null,
    "status": "ABERTO",
    "data_abertura": "2024-01-01T10:00:00",
    "data_fechamento": null,
    "data_hora_abertura": "2024-01-01T10:00:00",
    "data_hora_fechamento": null
  }
]
```

#### 2.6. Recalcular Saldo Esperado
```http
POST /api/caixa/admin/aberturas/{caixa_abertura_id}/recalcular-saldo
```

**Response:** `200 OK` (mesmo formato do abrir, com saldo_esperado atualizado)

**Validações:**
- A abertura deve estar aberta

#### 2.7. Valores Esperados por Tipo de Pagamento
```http
GET /api/caixa/admin/aberturas/{caixa_abertura_id}/valores-esperados
```

**Response:** `200 OK`
```json
{
  "caixa_abertura_id": 1,
  "caixa_id": 1,
  "empresa_id": 1,
  "data_abertura": "2024-01-01T10:00:00",
  "valor_inicial_dinheiro": 100.00,
  "valores_por_meio": [
    {
      "meio_pagamento_id": 1,
      "meio_pagamento_nome": "Dinheiro",
      "meio_pagamento_tipo": "DINHEIRO",
      "valor_esperado": 200.00,
      "quantidade_transacoes": 10
    },
    {
      "meio_pagamento_id": 2,
      "meio_pagamento_nome": "Cartão de Crédito",
      "meio_pagamento_tipo": "CARTAO_CREDITO",
      "valor_esperado": 500.00,
      "quantidade_transacoes": 15
    }
  ],
  "total_esperado_dinheiro": 250.00
}
```

**Validações:**
- A abertura deve estar aberta

#### 2.8. Conferências da Abertura Fechada
```http
GET /api/caixa/admin/aberturas/{caixa_abertura_id}/conferencias
```

**Response:** `200 OK`
```json
{
  "caixa_abertura_id": 1,
  "conferencias": [
    {
      "meio_pagamento_id": 1,
      "meio_pagamento_nome": "Dinheiro",
      "meio_pagamento_tipo": "DINHEIRO",
      "valor_esperado": 200.00,
      "valor_conferido": 195.00,
      "diferenca": -5.00,
      "quantidade_transacoes": 10,
      "observacoes": "Faltou R$ 5,00"
    }
  ]
}
```

---

## 3. Retiradas

### Endpoints

#### 3.1. Criar Retirada
```http
POST /api/caixa/admin/aberturas/{caixa_abertura_id}/retiradas
```

**Body:**
```json
{
  "tipo": "SANGRIA",
  "valor": 50.00,
  "observacoes": "Sangria para troco"
}
```

**Tipos:**
- `SANGRIA`: Retirada de dinheiro para troco
- `DESPESA`: Despesa do caixa (observações obrigatórias)

**Response:** `201 Created`
```json
{
  "id": 1,
  "caixa_abertura_id": 1,
  "tipo": "SANGRIA",
  "valor": 50.00,
  "observacoes": "Sangria para troco",
  "usuario_id": 1,
  "usuario_nome": "João",
  "created_at": "2024-01-01T12:00:00"
}
```

**Validações:**
- A abertura deve estar aberta
- Para `DESPESA`, `observacoes` é obrigatório

#### 3.2. Listar Retiradas
```http
GET /api/caixa/admin/aberturas/{caixa_abertura_id}/retiradas?tipo=SANGRIA
```

**Query Parameters:**
- `tipo` (opcional): Filtrar por tipo (SANGRIA ou DESPESA)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "caixa_abertura_id": 1,
    "tipo": "SANGRIA",
    "valor": 50.00,
    "observacoes": "Sangria para troco",
    "usuario_id": 1,
    "usuario_nome": "João",
    "created_at": "2024-01-01T12:00:00"
  }
]
```

#### 3.3. Excluir Retirada
```http
DELETE /api/caixa/admin/aberturas/retiradas/{retirada_id}
```

**Response:** `204 No Content`

**Validações:**
- A abertura deve estar aberta

---

## Fluxo de Uso Recomendado

### 1. Cadastrar Caixas
1. Criar caixas usando o CRUD (`POST /api/caixa/admin/caixas/`)
2. Listar caixas disponíveis (`GET /api/caixa/admin/caixas/`)

### 2. Abrir Caixa
1. Verificar se há abertura aberta (`GET /api/caixa/admin/aberturas/aberto/{empresa_id}?caixa_id={caixa_id}`)
2. Se não houver, abrir nova abertura (`POST /api/caixa/admin/aberturas/abrir`)

### 3. Durante o Dia
1. Consultar valores esperados (`GET /api/caixa/admin/aberturas/{caixa_abertura_id}/valores-esperados`)
2. Registrar retiradas se necessário (`POST /api/caixa/admin/aberturas/{caixa_abertura_id}/retiradas`)
3. Recalcular saldo se necessário (`POST /api/caixa/admin/aberturas/{caixa_abertura_id}/recalcular-saldo`)

### 4. Fechar Caixa
1. Consultar valores esperados (`GET /api/caixa/admin/aberturas/{caixa_abertura_id}/valores-esperados`)
2. Fechar abertura com conferências (`POST /api/caixa/admin/aberturas/{caixa_abertura_id}/fechar`)
3. Consultar conferências após fechamento (`GET /api/caixa/admin/aberturas/{caixa_abertura_id}/conferencias`)

---

## Códigos de Erro

- `400 Bad Request`: Dados inválidos ou regra de negócio violada
- `404 Not Found`: Recurso não encontrado
- `500 Internal Server Error`: Erro interno do servidor

---

## Autenticação

Todos os endpoints requerem autenticação via token JWT no header:
```
Authorization: Bearer {token}
```

