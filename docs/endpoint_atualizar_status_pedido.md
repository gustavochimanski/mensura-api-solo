# Documentação: Atualizar Status de Pedido

## Endpoint

```
PATCH /api/pedidos/admin/{pedido_id}/status
```

---

## Descrição

Atualiza o status de um pedido (delivery, mesa ou balcão). Esta rota funciona para todos os tipos de pedidos unificados.

---

## Autenticação

Requer autenticação de administrador via `get_current_user`.

---

## Parâmetros

### Path Parameters

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | `integer` | Sim | ID do pedido (deve ser > 0) |

### Request Body

```json
{
  "status": "S"
}
```

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `status` | `string` (enum) | Sim | Novo status do pedido. Valores válidos: `P`, `I`, `R`, `E`, `C`, `D`, `X`, `A`, `S` |

---

## Status Válidos

| Código | Descrição | Quando Usar |
|--------|-----------|-------------|
| `P` | Pendente | Pedido recém-criado, aguardando processamento |
| `I` | Pendente Impressão | Pedido aguardando impressão na cozinha |
| `R` | Em Preparo | Pedido em preparação |
| `S` | Saiu para entrega | Pedido saiu para entrega (delivery) |
| `E` | Entregue | Pedido finalizado/entregue |
| `C` | Cancelado | Pedido cancelado |
| `D` | Editado | Pedido foi editado |
| `X` | Em Edição | Pedido está sendo editado |
| `A` | Aguardando Pagamento | Aguardando confirmação de pagamento |

---

## Resposta

### Sucesso (200 OK)

Retorna um objeto `PedidoResponseCompleto` com os dados atualizados do pedido:

```json
{
  "id": 12,
  "status": "S",
  "tipo_entrega": "DELIVERY",
  "valor_total": 45.90,
  "cliente": {
    "id": 789,
    "nome": "Maria Santos"
  },
  "entregador": {
    "id": 123,
    "nome": "João Silva"
  },
  // ... outros campos do pedido
}
```

---

## Validações

1. **Pedido Existe**: O pedido deve existir no sistema.
2. **Status Válido**: O status deve ser um dos valores permitidos do enum.
3. **Transições de Status**: Algumas transições podem ter regras de negócio específicas.

---

## Comportamento Especial por Status

### Status `S` (Saiu para entrega)
- Se o pedido tiver um entregador vinculado, envia notificação WhatsApp automática com a rota de entrega.

### Status `E` (Entregue)
- Para pedidos de mesa/balcão, fecha a conta automaticamente.
- Verifica se há outros pedidos abertos na mesa antes de liberá-la.

### Status `C` (Cancelado)
- Para pedidos de mesa/balcão, verifica se há outros pedidos abertos antes de liberar a mesa.

---

## Códigos de Erro

| Código | Descrição |
|--------|-----------|
| `200` | Sucesso |
| `400` | Status inválido ou transição não permitida |
| `404` | Pedido não encontrado |
| `500` | Erro interno do servidor |

---

## Exemplos de Uso

### Exemplo 1: Atualizar Status para "Saiu para entrega"

**Request:**
```http
PATCH /api/pedidos/admin/12/status HTTP/1.1
Content-Type: application/json
Authorization: Bearer {token}

{
  "status": "S"
}
```

**Response:**
```json
{
  "id": 12,
  "status": "S",
  "tipo_entrega": "DELIVERY",
  "entregador_id": 123,
  "entregador": {
    "id": 123,
    "nome": "João Silva"
  },
  "valor_total": 45.90
}
```

### Exemplo 2: Atualizar Status para "Preparando"

**Request:**
```http
PATCH /api/pedidos/admin/12/status HTTP/1.1
Content-Type: application/json
Authorization: Bearer {token}

{
  "status": "R"
}
```

**Response:**
```json
{
  "id": 12,
  "status": "R",
  "tipo_entrega": "DELIVERY",
  "valor_total": 45.90
}
```

### Exemplo 3: Atualizar Status para "Entregue"

**Request:**
```http
PATCH /api/pedidos/admin/12/status HTTP/1.1
Content-Type: application/json
Authorization: Bearer {token}

{
  "status": "E"
}
```

**Response:**
```json
{
  "id": 12,
  "status": "E",
  "tipo_entrega": "DELIVERY",
  "valor_total": 45.90
}
```

### Exemplo 4: Erro - Pedido Não Encontrado

**Request:**
```http
PATCH /api/pedidos/admin/99999/status HTTP/1.1
Content-Type: application/json
Authorization: Bearer {token}

{
  "status": "S"
}
```

**Response:**
```json
{
  "detail": "Pedido não encontrado"
}
```

Status: `404 Not Found`

---

## ⚠️ Rota Antiga (Não Existe Mais)

A rota antiga `/api/cardapio/admin/pedidos/status/{pedido_id}?novo_status=S` **não existe mais**.

**Use a nova rota:**
```
PATCH /api/pedidos/admin/{pedido_id}/status
```

**Com o body:**
```json
{
  "status": "S"
}
```

---

## Observações

1. **Histórico**: Todas as alterações de status são registradas no histórico do pedido com o usuário que fez a alteração.

2. **Notificações**: Algumas mudanças de status podem disparar notificações automáticas (ex: WhatsApp para entregador quando status muda para "S").

3. **Regras de Negócio**: Algumas transições de status podem ter validações específicas dependendo do tipo de pedido (delivery, mesa, balcão).

4. **Idempotência**: Atualizar para o mesmo status não causa erro, mas registra no histórico.

---

## Schema de Request

```python
class PedidoStatusPatchRequest(BaseModel):
    status: PedidoStatusEnum = Field(description="Novo status do pedido.")
```

---

## Implementação

- **Router**: `app/api/pedidos/router/admin/router_pedidos_admin.py`
- **Service**: `app/api/pedidos/services/service_pedido_admin.py`
- **Service Core**: `app/api/pedidos/services/service_pedido.py`
- **Schema**: `app/api/pedidos/schemas/schema_pedido_admin.py`

---

## Migração da Rota Antiga

Se você estava usando a rota antiga:
```
GET /api/cardapio/admin/pedidos/status/{pedido_id}?novo_status=S
```

**Migre para:**
```
PATCH /api/pedidos/admin/{pedido_id}/status
```

**Com body JSON:**
```json
{
  "status": "S"
}
```

**Mudanças principais:**
- ✅ Método: `GET` → `PATCH`
- ✅ Path: `/api/cardapio/admin/pedidos/status/{id}` → `/api/pedidos/admin/{id}/status`
- ✅ Parâmetro: Query `novo_status` → Body `status`
- ✅ Formato: Query string → JSON body

