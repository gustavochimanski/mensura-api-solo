# Documentação: Listar Pedidos de uma Mesa

## ⚠️ Rota Antiga (Não Existe)

A rota `/api/mesas/admin/pedidos?empresa_id=1` **não existe mais** e retorna 404.

---

## Opções Disponíveis

Existem **duas formas** de listar pedidos de uma mesa:

### Opção 1: Via Rota de Pedidos (Recomendado)
Lista todos os pedidos de uma mesa específica com filtros avançados.

### Opção 2: Via Rota de Mesas
Obtém uma mesa específica com seus pedidos abertos incluídos.

---

## Opção 1: Listar Pedidos via Rota de Pedidos

### Endpoint

```
GET /api/pedidos/admin
```

### Descrição

Lista pedidos com filtros avançados, incluindo filtro por `mesa_id`. Permite filtrar por status, data, tipo de pedido, etc.

### Parâmetros de Query

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `empresa_id` | `integer` | Não | Filtra por empresa |
| `mesa_id` | `integer` | Não | **Filtra por mesa específica** |
| `tipo` | `array[string]` | Não | Filtra por tipo: `DELIVERY`, `RETIRADA`, `BALCAO`, `MESA` |
| `status_filter` | `array[string]` | Não | Filtra por status: `P`, `I`, `R`, `S`, `E`, `C`, etc. |
| `cliente_id` | `integer` | Não | Filtra por cliente |
| `data_inicio` | `date` | Não | Data inicial (YYYY-MM-DD) |
| `data_fim` | `date` | Não | Data final (YYYY-MM-DD) |
| `skip` | `integer` | Não | Quantidade de registros a pular (padrão: 0) |
| `limit` | `integer` | Não | Limite de registros (padrão: 50, máx: 200) |

### Exemplos

#### Exemplo 1: Listar Todos os Pedidos de uma Mesa

**Request:**
```http
GET /api/pedidos/admin?mesa_id=5&empresa_id=1 HTTP/1.1
```

**Response:**
```json
[
  {
    "id": 123,
    "status": "P",
    "tipo_entrega": "MESA",
    "mesa_id": 5,
    "valor_total": 45.90,
    "cliente": {
      "id": 789,
      "nome": "Maria Santos"
    },
    "data_criacao": "2024-01-15T10:30:00Z"
  },
  {
    "id": 124,
    "status": "R",
    "tipo_entrega": "MESA",
    "mesa_id": 5,
    "valor_total": 32.50,
    "cliente": {
      "id": 790,
      "nome": "João Silva"
    },
    "data_criacao": "2024-01-15T11:00:00Z"
  }
]
```

#### Exemplo 2: Listar Apenas Pedidos Abertos de uma Mesa

**Request:**
```http
GET /api/pedidos/admin?mesa_id=5&empresa_id=1&status_filter=P&status_filter=I&status_filter=R HTTP/1.1
```

**Response:**
```json
[
  {
    "id": 123,
    "status": "P",
    "tipo_entrega": "MESA",
    "mesa_id": 5,
    "valor_total": 45.90
  }
]
```

#### Exemplo 3: Listar Pedidos de Mesa e Balcão de uma Mesa

**Request:**
```http
GET /api/pedidos/admin?mesa_id=5&empresa_id=1&tipo=MESA&tipo=BALCAO HTTP/1.1
```

**Response:**
```json
[
  {
    "id": 123,
    "status": "P",
    "tipo_entrega": "MESA",
    "mesa_id": 5,
    "valor_total": 45.90
  },
  {
    "id": 125,
    "status": "R",
    "tipo_entrega": "BALCAO",
    "mesa_id": 5,
    "valor_total": 28.00
  }
]
```

#### Exemplo 4: Listar Pedidos de uma Mesa em um Período

**Request:**
```http
GET /api/pedidos/admin?mesa_id=5&empresa_id=1&data_inicio=2024-01-15&data_fim=2024-01-15 HTTP/1.1
```

---

## Opção 2: Obter Mesa com Pedidos Abertos

### Endpoint

```
GET /api/mesas/admin/mesas/{mesa_id}
```

### Descrição

Obtém uma mesa específica com seus **pedidos abertos** incluídos no campo `pedidos_abertos`. Esta rota retorna apenas pedidos que ainda não foram finalizados (status diferente de `E` - Entregue).

### Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `mesa_id` | `integer` (path) | Sim | ID da mesa |
| `empresa_id` | `integer` (query) | Sim | ID da empresa |

### Exemplo

**Request:**
```http
GET /api/mesas/admin/mesas/5?empresa_id=1 HTTP/1.1
```

**Response:**
```json
{
  "id": 5,
  "codigo": "5",
  "numero": "5",
  "descricao": "Mesa 5",
  "capacidade": 4,
  "status": "O",
  "status_descricao": "Ocupada",
  "ativa": "S",
  "label": "Mesa 5",
  "num_pessoas_atual": 3,
  "empresa_id": 1,
  "pedidos_abertos": [
    {
      "id": 123,
      "numero_pedido": "123",
      "status": "P",
      "num_pessoas": 2,
      "valor_total": 45.90,
      "cliente_id": 789,
      "cliente_nome": "Maria Santos"
    },
    {
      "id": 125,
      "numero_pedido": "125",
      "status": "R",
      "num_pessoas": 1,
      "valor_total": 28.00,
      "cliente_id": 790,
      "cliente_nome": "João Silva"
    }
  ]
}
```

### Observações sobre Pedidos Abertos

O campo `pedidos_abertos` inclui:
- **Pedidos de mesa** (tipo `MESA`) vinculados à mesa
- **Pedidos de balcão** (tipo `BALCAO`) vinculados à mesa
- Apenas pedidos com status diferente de `E` (Entregue) e `C` (Cancelado)

---

## Comparação das Opções

| Característica | Opção 1: `/api/pedidos/admin` | Opção 2: `/api/mesas/admin/mesas/{id}` |
|----------------|------------------------------|---------------------------------------|
| **Filtro por mesa** | ✅ Sim (`mesa_id`) | ✅ Sim (via path) |
| **Filtro por status** | ✅ Sim | ❌ Não (só abertos) |
| **Filtro por data** | ✅ Sim | ❌ Não |
| **Filtro por tipo** | ✅ Sim | ❌ Não (inclui mesa e balcão) |
| **Paginação** | ✅ Sim | ❌ Não |
| **Informações da mesa** | ❌ Não | ✅ Sim |
| **Pedidos finalizados** | ✅ Sim | ❌ Não |
| **Uso recomendado** | Listagem completa com filtros | Visualização rápida da mesa |

---

## Quando Usar Cada Opção

### Use Opção 1 (`/api/pedidos/admin`) quando:
- ✅ Precisa filtrar por status específico
- ✅ Precisa ver pedidos finalizados
- ✅ Precisa filtrar por data/período
- ✅ Precisa paginação
- ✅ Precisa apenas dos dados dos pedidos (não da mesa)

### Use Opção 2 (`/api/mesas/admin/mesas/{id}`) quando:
- ✅ Precisa ver informações da mesa junto com os pedidos
- ✅ Precisa apenas dos pedidos abertos
- ✅ Quer uma resposta mais simples e direta
- ✅ Está trabalhando no contexto de gerenciamento de mesas

---

## Migração da Rota Antiga

Se você estava usando:
```
GET /api/mesas/admin/pedidos?empresa_id=1
```

**Migre para uma das opções:**

### Para listar todos os pedidos de todas as mesas:
```
GET /api/pedidos/admin?empresa_id=1&tipo=MESA
```

### Para listar pedidos de uma mesa específica:
```
GET /api/pedidos/admin?mesa_id={mesa_id}&empresa_id=1
```

### Para obter uma mesa com seus pedidos abertos:
```
GET /api/mesas/admin/mesas/{mesa_id}?empresa_id=1
```

---

## Códigos de Erro

| Código | Descrição |
|--------|-----------|
| `200` | Sucesso |
| `400` | Parâmetros inválidos |
| `404` | Mesa não encontrada (Opção 2) |
| `401` | Não autenticado |
| `403` | Sem permissão |

---

## Implementação

- **Router Pedidos**: `app/api/pedidos/router/admin/router_pedidos_admin.py`
- **Router Mesas**: `app/api/cadastros/router/admin/router_mesas.py`
- **Service Pedidos**: `app/api/pedidos/services/service_pedido_admin.py`
- **Service Mesas**: `app/api/cadastros/services/service_mesas.py`

