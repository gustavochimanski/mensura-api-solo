# Documentação: Fechar Conta - Pedidos Delivery/Retirada

## Endpoint

```
PATCH /api/pedidos/admin/{pedido_id}/fechar-conta
```

---

## Descrição

Fecha a conta de um pedido de **delivery** ou **retirada**, marcando-o como **pago** sem alterar o status do pedido. Este endpoint substitui a funcionalidade anterior de setar status "E" (Entregue) para pedidos delivery.

**Importante:** 
- Para pedidos de **delivery/retirada**, este endpoint marca como pago mas **não altera o status** do pedido.
- Para pedidos de **mesa/balcão**, este endpoint fecha a conta e altera o status para "E" (Entregue).

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
  "meio_pagamento_id": 1,
  "troco_para": 10.50
}
```

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `meio_pagamento_id` | `integer` | Não | ID do meio de pagamento utilizado |
| `troco_para` | `float` | Não | Valor informado para troco (quando aplicável) |

---

## Resposta

### Sucesso (200 OK)

Retorna um objeto `PedidoResponseCompleto` com os dados atualizados do pedido:

```json
{
  "id": 123,
  "status": "S",
  "tipo_entrega": "DELIVERY",
  "pago": true,
  "meio_pagamento_id": 1,
  "troco_para": 10.50,
  "valor_total": 45.90,
  "cliente": {
    "id": 789,
    "nome": "Maria Santos"
  },
  // ... outros campos do pedido
}
```

### Campos de Resposta Relevantes

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `pago` | `boolean` | **Novo campo** - Indica se o pedido foi pago (true após fechar conta) |
| `meio_pagamento_id` | `integer \| null` | ID do meio de pagamento utilizado |
| `troco_para` | `float \| null` | Valor informado para troco |
| `status` | `string` | Status atual do pedido (não é alterado para delivery) |

---

## Validações

1. **Pedido Existe**: O pedido deve existir no sistema.
2. **Tipo de Pedido**: Funciona para todos os tipos (DELIVERY, RETIRADA, MESA, BALCAO).
3. **Meio de Pagamento**: Se fornecido, deve existir e estar ativo.

---

## Comportamento por Tipo de Pedido

### Delivery / Retirada
- ✅ Marca `pago = true`
- ✅ Atualiza `meio_pagamento_id` (se fornecido)
- ✅ Atualiza `troco_para` (se fornecido)
- ❌ **NÃO altera o status** do pedido
- ✅ Registra no histórico do pedido

### Mesa / Balcão
- ✅ Marca `pago = true`
- ✅ Atualiza `meio_pagamento_id` (se fornecido)
- ✅ Atualiza `troco_para` (se fornecido)
- ✅ **Altera status para "E" (Entregue)**
- ✅ Verifica se há outros pedidos abertos antes de liberar a mesa
- ✅ Registra no histórico do pedido

---

## Mudanças Importantes

### ⚠️ Status "E" Bloqueado para Delivery

**Antes:**
```http
PATCH /api/pedidos/admin/123/status
{
  "status": "E"
}
```
✅ Funcionava para todos os tipos de pedido

**Agora:**
```http
PATCH /api/pedidos/admin/123/status
{
  "status": "E"
}
```
❌ **Retorna erro 400** para pedidos delivery/retirada:
```json
{
  "detail": "Não é possível setar status 'Entregue' para pedidos de delivery/retirada. Use o endpoint 'fechar-conta' para marcar o pedido como pago."
}
```

**Solução:**
```http
PATCH /api/pedidos/admin/123/fechar-conta
{
  "meio_pagamento_id": 1
}
```
✅ Marca como pago sem alterar status

---

## Códigos de Erro

| Código | Descrição |
|--------|-----------|
| `200` | Sucesso |
| `400` | Meio de pagamento inválido ou inativo |
| `404` | Pedido não encontrado |
| `500` | Erro interno do servidor |

---

## Exemplos de Uso

### Exemplo 1: Fechar Conta Delivery com Meio de Pagamento

**Request:**
```http
PATCH /api/pedidos/admin/123/fechar-conta HTTP/1.1
Content-Type: application/json
Authorization: Bearer {token}

{
  "meio_pagamento_id": 1
}
```

**Response:**
```json
{
  "id": 123,
  "status": "S",
  "tipo_entrega": "DELIVERY",
  "pago": true,
  "meio_pagamento_id": 1,
  "valor_total": 45.90,
  "cliente": {
    "id": 789,
    "nome": "Maria Santos"
  }
}
```

### Exemplo 2: Fechar Conta com Troco

**Request:**
```http
PATCH /api/pedidos/admin/123/fechar-conta HTTP/1.1
Content-Type: application/json
Authorization: Bearer {token}

{
  "meio_pagamento_id": 2,
  "troco_para": 10.50
}
```

**Response:**
```json
{
  "id": 123,
  "status": "S",
  "tipo_entrega": "DELIVERY",
  "pago": true,
  "meio_pagamento_id": 2,
  "troco_para": 10.50,
  "valor_total": 45.90
}
```

### Exemplo 3: Fechar Conta sem Meio de Pagamento

**Request:**
```http
PATCH /api/pedidos/admin/123/fechar-conta HTTP/1.1
Content-Type: application/json
Authorization: Bearer {token}

{}
```

**Response:**
```json
{
  "id": 123,
  "status": "S",
  "tipo_entrega": "DELIVERY",
  "pago": true,
  "meio_pagamento_id": null,
  "valor_total": 45.90
}
```

### Exemplo 4: Erro - Meio de Pagamento Inválido

**Request:**
```http
PATCH /api/pedidos/admin/123/fechar-conta HTTP/1.1
Content-Type: application/json
Authorization: Bearer {token}

{
  "meio_pagamento_id": 999
}
```

**Response:**
```json
{
  "detail": "Meio de pagamento inválido ou inativo"
}
```

Status: `400 Bad Request`

---

## Nova Coluna no Banco de Dados

### SQL para Adicionar Coluna `pago`

Execute o seguinte SQL no banco de dados:

```sql
-- Adicionar coluna 'pago' na tabela pedidos.pedidos
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'pedidos' 
        AND table_name = 'pedidos' 
        AND column_name = 'pago'
    ) THEN
        ALTER TABLE pedidos.pedidos 
        ADD COLUMN pago BOOLEAN NOT NULL DEFAULT FALSE;
        
        -- Cria índice para melhorar performance de consultas
        CREATE INDEX IF NOT EXISTS idx_pedidos_pago 
        ON pedidos.pedidos(pago) 
        WHERE pago = TRUE;
        
        RAISE NOTICE 'Coluna pago adicionada com sucesso na tabela pedidos.pedidos';
    ELSE
        RAISE NOTICE 'Coluna pago já existe na tabela pedidos.pedidos';
    END IF;
END $$;
```

### Estrutura da Coluna

| Coluna | Tipo | Nullable | Default | Descrição |
|--------|------|----------|---------|-----------|
| `pago` | `BOOLEAN` | `NOT NULL` | `FALSE` | Indica se o pedido foi pago |

---

## Observações

1. **Status vs Pago**: 
   - O campo `pago` é independente do `status`
   - Um pedido delivery pode estar `pago = true` mas com `status = "S"` (Saiu para entrega)

2. **Histórico**: 
   - A operação de fechar conta é registrada no histórico do pedido
   - Inclui informações sobre o meio de pagamento utilizado

3. **Idempotência**: 
   - Fechar conta múltiplas vezes não causa erro
   - O campo `pago` será sempre `true` após a primeira chamada

4. **Compatibilidade**: 
   - Pedidos antigos terão `pago = false` por padrão
   - Use o endpoint para marcar pedidos antigos como pagos se necessário

---

## Schema de Request

```python
class PedidoFecharContaRequest(BaseModel):
    """Payload unificado para fechamento de conta."""
    
    meio_pagamento_id: Optional[int] = Field(
        default=None,
        description="ID do meio de pagamento utilizado no fechamento.",
    )
    troco_para: Optional[float] = Field(
        default=None,
        description="Valor informado para troco (quando aplicável).",
    )
```

---

## Implementação

- **Router**: `app/api/pedidos/router/admin/router_pedidos_admin.py`
- **Service**: `app/api/pedidos/services/service_pedido_admin.py`
- **Model**: `app/api/pedidos/models/model_pedido_unificado.py`
- **Schema**: `app/api/pedidos/schemas/schema_pedido_admin.py`

---

## Guia de Migração para o Front

### 1. Atualizar Chamadas de Status "E"

**Antes:**
```typescript
// ❌ Não funciona mais para delivery
await api.patch(`/api/pedidos/admin/${pedidoId}/status`, {
  status: "E"
});
```

**Depois:**
```typescript
// ✅ Use fechar-conta para delivery
await api.patch(`/api/pedidos/admin/${pedidoId}/fechar-conta`, {
  meio_pagamento_id: meioPagamentoId,
  troco_para: trocoPara // opcional
});
```

### 2. Adicionar Campo `pago` nas Interfaces

```typescript
interface Pedido {
  id: number;
  status: string;
  pago: boolean; // ✅ Novo campo
  meio_pagamento_id: number | null;
  troco_para: number | null;
  // ... outros campos
}
```

### 3. Exibir Status de Pagamento

```typescript
// Exemplo de componente
function StatusPagamento({ pedido }: { pedido: Pedido }) {
  if (pedido.pago) {
    return <Badge color="green">Pago</Badge>;
  }
  return <Badge color="orange">Pendente</Badge>;
}
```

### 4. Filtrar Pedidos Pagos

```typescript
// Filtrar pedidos pagos
const pedidosPagos = pedidos.filter(p => p.pago);

// Filtrar pedidos não pagos
const pedidosPendentes = pedidos.filter(p => !p.pago);
```

### 5. Validação ao Setar Status "E"

```typescript
// Adicionar validação no front
async function atualizarStatus(pedidoId: number, novoStatus: string) {
  if (novoStatus === "E") {
    const pedido = await obterPedido(pedidoId);
    
    if (pedido.tipo_entrega === "DELIVERY" || pedido.tipo_entrega === "RETIRADA") {
      // Mostrar erro ou redirecionar para fechar-conta
      throw new Error(
        "Use o endpoint 'fechar-conta' para marcar pedidos delivery como pagos"
      );
    }
  }
  
  // Continuar com atualização de status normal
  return api.patch(`/api/pedidos/admin/${pedidoId}/status`, {
    status: novoStatus
  });
}
```

---

## Checklist de Implementação

- [ ] Executar SQL para adicionar coluna `pago`
- [ ] Atualizar interfaces TypeScript com campo `pago`
- [ ] Substituir chamadas de status "E" por `fechar-conta` para delivery
- [ ] Adicionar validação para bloquear status "E" em delivery no front
- [ ] Atualizar UI para exibir status de pagamento
- [ ] Adicionar filtros por `pago` nas listagens
- [ ] Testar fluxo completo de fechamento de conta

