# 📘 Documentação Frontend: Adicionar Item em Pedido

## 🎯 Endpoint Unificado

**POST** `/api/pedidos/admin/{pedido_id}/itens`

Este endpoint funciona **exatamente igual** para todos os tipos de pedido: **Delivery**, **Mesa** e **Balcão**.

---

## 🔐 Autenticação

**Header obrigatório:**
```
Authorization: Bearer {token_admin}
Content-Type: application/json
```

---

## 📋 Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | `integer` | ✅ Sim | ID do pedido (deve ser > 0) |

**Exemplo:**
```
POST /api/pedidos/admin/21/itens
```

---

## 📦 Body Request

### Schema Completo

```typescript
interface PedidoItemMutationRequest {
  acao: "ADD" | "UPDATE" | "REMOVE";
  item_id?: number;                    // Obrigatório para UPDATE/REMOVE
  produto_cod_barras?: string;         // Para produto simples
  receita_id?: number;                 // Para receita
  combo_id?: number;                   // Para combo
  quantidade?: number;                 // >= 1, obrigatório para ADD/UPDATE
  observacao?: string | null;          // Observação livre (não use "$undefined")
  complementos?: Array<{                // Apenas para Mesa/Balcão
    complemento_id: number;
    adicionais: Array<{
      adicional_id: number;
      quantidade: number;              // >= 1
    }>;
  }>;
}
```

### Regras Importantes

1. **Para adicionar (`acao: "ADD"`):**
   - Deve informar **exatamente um** dos seguintes:
     - `produto_cod_barras` (produto simples)
     - `receita_id` (receita)
     - `combo_id` (combo)
   - `quantidade` é obrigatório (>= 1)
   - `complementos` são opcionais (apenas Mesa/Balcão)

2. **Para atualizar (`acao: "UPDATE"`):**
   - `item_id` é obrigatório
   - `quantidade` e/ou `observacao` podem ser atualizados

3. **Para remover (`acao: "REMOVE"`):**
   - `item_id` é obrigatório

---

## 📝 Exemplos Práticos

### 1. Adicionar Produto Simples

```json
{
  "acao": "ADD",
  "produto_cod_barras": "7891234567890",
  "quantidade": 2,
  "observacao": "Sem cebola"
}
```

**Funciona em:** Delivery, Mesa e Balcão ✅

---

### 2. Adicionar Receita

```json
{
  "acao": "ADD",
  "receita_id": 2,
  "quantidade": 1,
  "observacao": "Bem passado"
}
```

**Funciona em:** Delivery, Mesa e Balcão ✅

---

### 3. Adicionar Combo

```json
{
  "acao": "ADD",
  "combo_id": 8,
  "quantidade": 1,
  "observacao": "Combo completo"
}
```

**Funciona em:** Delivery, Mesa e Balcão ✅

---

### 4. Adicionar Receita com Complementos (Apenas Mesa/Balcão)

```json
{
  "acao": "ADD",
  "receita_id": 2,
  "quantidade": 1,
  "observacao": "Bem passado",
  "complementos": [
    {
      "complemento_id": 3,
      "adicionais": [
        {
          "adicional_id": 10,
          "quantidade": 1
        },
        {
          "adicional_id": 2,
          "quantidade": 1
        }
      ]
    }
  ]
}
```

**Funciona em:** Mesa e Balcão ✅  
**Não funciona em:** Delivery ❌ (complementos não são suportados)

---

### 5. Atualizar Item Existente

```json
{
  "acao": "UPDATE",
  "item_id": 45,
  "quantidade": 3,
  "observacao": "Atualizado: agora são 3 unidades"
}
```

**Funciona em:** Delivery, Mesa e Balcão ✅

---

### 6. Remover Item

```json
{
  "acao": "REMOVE",
  "item_id": 45
}
```

**Funciona em:** Delivery, Mesa e Balcão ✅

---

## ⚠️ Erros Comuns do Frontend

### ❌ ERRADO - Ação com valor incorreto
```json
{
  "acao": "adicionar"  // ❌ ERRADO - deve ser "ADD"
}
```

### ✅ CORRETO
```json
{
  "acao": "ADD"  // ✅ CORRETO
}
```

---

### ❌ ERRADO - Adicionais no nível raiz
```json
{
  "acao": "ADD",
  "receita_id": 2,
  "adicionais": [  // ❌ ERRADO - adicionais devem estar dentro de complementos
    {"adicional_id": 10, "quantidade": 1}
  ]
}
```

### ✅ CORRETO
```json
{
  "acao": "ADD",
  "receita_id": 2,
  "complementos": [  // ✅ CORRETO
    {
      "complemento_id": 3,
      "adicionais": [
        {"adicional_id": 10, "quantidade": 1}
      ]
    }
  ]
}
```

---

### ❌ ERRADO - Observação como string "$undefined"
```json
{
  "observacao": "$undefined"  // ❌ ERRADO - use null ou omita o campo
}
```

### ✅ CORRETO
```json
{
  "observacao": null  // ✅ CORRETO
}
// ou simplesmente omita o campo
```

---

### ❌ ERRADO - Múltiplos identificadores
```json
{
  "acao": "ADD",
  "produto_cod_barras": "123",
  "receita_id": 2  // ❌ ERRADO - informe apenas um tipo
}
```

### ✅ CORRETO
```json
{
  "acao": "ADD",
  "receita_id": 2  // ✅ CORRETO - apenas receita_id
}
```

---

## ✅ Resposta de Sucesso

**Status Code:** `200 OK`

```typescript
interface PedidoResponse {
  id: number;
  status: string;  // "P", "A", "E", etc.
  cliente_id: number | null;
  empresa_id: number;
  tipo_entrega: "DELIVERY" | "RETIRADA" | "BALCAO" | "MESA";
  subtotal: number;
  desconto: number;
  taxa_entrega: number;
  taxa_servico: number;
  valor_total: number;
  data_criacao: string;  // ISO 8601
  data_atualizacao: string;  // ISO 8601
  itens: Array<{
    id: number;
    produto_cod_barras: string | null;
    combo_id: number | null;
    receita_id: number | null;
    quantidade: number;
    preco_unitario: number;
    observacao: string | null;
    produto_descricao_snapshot: string | null;
    produto_imagem_snapshot: string | null;
  }>;
  // ... outros campos
}
```

---

## ❌ Respostas de Erro

### 400 Bad Request - Validação

```json
{
  "detail": "É necessário informar produto_cod_barras, receita_id ou combo_id"
}
```

**Outros erros comuns:**
- `"produto_cod_barras é obrigatório para adicionar item simples em pedidos de delivery."`
- `"item_id é obrigatório para remover item"`
- `"Quantidade deve ser maior que zero"`
- `"Complementos não são suportados para pedidos de delivery."`

### 404 Not Found

```json
{
  "detail": "Pedido não encontrado"
}
```

ou

```json
{
  "detail": "Produto não encontrado"
}
```

### 400 Bad Request - Produto indisponível

```json
{
  "detail": "Produto não disponível"
}
```

ou

```json
{
  "detail": "Receita não disponível"
}
```

ou

```json
{
  "detail": "Combo não disponível"
}
```

### 400 Bad Request - Pedido fechado/cancelado

```json
{
  "detail": "Pedido fechado/cancelado"
}
```

---

## 💡 Implementação TypeScript/JavaScript

```typescript
// Tipos
type AcaoItem = "ADD" | "UPDATE" | "REMOVE";

interface ComplementoRequest {
  complemento_id: number;
  adicionais: Array<{
    adicional_id: number;
    quantidade: number;
  }>;
}

interface PedidoItemMutationRequest {
  acao: AcaoItem;
  item_id?: number;
  produto_cod_barras?: string;
  receita_id?: number;
  combo_id?: number;
  quantidade?: number;
  observacao?: string | null;
  complementos?: ComplementoRequest[];
}

interface PedidoResponse {
  id: number;
  status: string;
  tipo_entrega: string;
  valor_total: number;
  itens: Array<{
    id: number;
    produto_cod_barras: string | null;
    combo_id: number | null;
    receita_id: number | null;
    quantidade: number;
    preco_unitario: number;
    observacao: string | null;
  }>;
  // ... outros campos
}

// Função para adicionar item
async function adicionarItemPedido(
  pedidoId: number,
  payload: PedidoItemMutationRequest,
  token: string
): Promise<PedidoResponse> {
  const response = await fetch(
    `/api/pedidos/admin/${pedidoId}/itens`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Erro ao adicionar item");
  }

  return response.json();
}

// Exemplos de uso

// 1. Adicionar produto simples
await adicionarItemPedido(21, {
  acao: "ADD",
  produto_cod_barras: "7891234567890",
  quantidade: 2,
  observacao: "Sem cebola"
}, token);

// 2. Adicionar receita
await adicionarItemPedido(21, {
  acao: "ADD",
  receita_id: 2,
  quantidade: 1,
  observacao: null
}, token);

// 3. Adicionar combo
await adicionarItemPedido(21, {
  acao: "ADD",
  combo_id: 8,
  quantidade: 1
}, token);

// 4. Adicionar receita com complementos (apenas Mesa/Balcão)
await adicionarItemPedido(21, {
  acao: "ADD",
  receita_id: 2,
  quantidade: 1,
  complementos: [
    {
      complemento_id: 3,
      adicionais: [
        { adicional_id: 10, quantidade: 1 },
        { adicional_id: 2, quantidade: 1 }
      ]
    }
  ]
}, token);

// 5. Atualizar item
await adicionarItemPedido(21, {
  acao: "UPDATE",
  item_id: 45,
  quantidade: 3,
  observacao: "Atualizado"
}, token);

// 6. Remover item
await adicionarItemPedido(21, {
  acao: "REMOVE",
  item_id: 45
}, token);
```

---

## 📌 Resumo das Regras

### ✅ O que funciona em TODOS os tipos (Delivery, Mesa, Balcão):

- ✅ Adicionar produto simples (`produto_cod_barras`)
- ✅ Adicionar receita (`receita_id`)
- ✅ Adicionar combo (`combo_id`)
- ✅ Atualizar item existente
- ✅ Remover item existente

### ⚠️ O que funciona APENAS em Mesa/Balcão:

- ✅ Complementos (`complementos` com `adicionais`)

### ❌ O que NÃO funciona em Delivery:

- ❌ Complementos (retornará erro 400 se enviado)

---

## 🔍 Validações do Frontend (Antes de Enviar)

Antes de fazer a requisição, valide no frontend:

1. ✅ `acao` deve ser exatamente `"ADD"`, `"UPDATE"` ou `"REMOVE"` (maiúsculas)
2. ✅ Para `ADD`: deve ter exatamente um de: `produto_cod_barras`, `receita_id` ou `combo_id`
3. ✅ Para `ADD`: `quantidade` deve ser >= 1
4. ✅ Para `UPDATE`/`REMOVE`: `item_id` deve ser informado
5. ✅ `observacao` deve ser `null` ou string válida (não `"$undefined"` ou `undefined`)
6. ✅ Se for pedido de Delivery: não enviar `complementos`
7. ✅ Se enviar `complementos`: `adicionais` devem estar dentro de `complementos`, não no nível raiz

---

## 📚 Referências

- Endpoint: `POST /api/pedidos/admin/{pedido_id}/itens`
- Schema completo: `app/api/pedidos/schemas/schema_pedido_admin.py`
- Implementação: `app/api/pedidos/services/service_pedido_admin.py`

---

## 🎯 Checklist para Implementação

- [ ] Implementar função `adicionarItemPedido` com tratamento de erros
- [ ] Validar `acao` antes de enviar (deve ser "ADD", "UPDATE" ou "REMOVE")
- [ ] Validar que apenas um tipo é enviado (produto_cod_barras OU receita_id OU combo_id)
- [ ] Validar `quantidade` >= 1 para ADD/UPDATE
- [ ] Validar `item_id` para UPDATE/REMOVE
- [ ] Tratar `observacao` como `null` ao invés de `"$undefined"` ou `undefined`
- [ ] Verificar tipo de pedido antes de permitir enviar `complementos` (apenas Mesa/Balcão)
- [ ] Estruturar `complementos` corretamente (adicionais dentro de complementos)
- [ ] Tratar erros 400, 404 e exibir mensagens amigáveis ao usuário
- [ ] Atualizar lista de itens após adicionar/atualizar/remover com sucesso

