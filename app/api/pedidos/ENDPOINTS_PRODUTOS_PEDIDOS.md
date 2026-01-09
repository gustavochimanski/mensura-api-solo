# Documentação de Endpoints - Gerenciamento de Produtos em Pedidos (UNIFICADO)

Esta documentação descreve os endpoints **unificados** para adicionar, atualizar e remover produtos em pedidos de **Delivery, Balcão e Mesa**.

## Base URL
```
/api/pedidos/admin
```

## Autenticação
Todos os endpoints requerem autenticação via token de administrador.

---

## 🎯 Endpoint Principal Unificado

Todos os tipos de pedido (Delivery, Balcão e Mesa) usam o **mesmo endpoint unificado**:

```
POST /api/pedidos/admin/{pedido_id}/itens
```

O tipo de pedido é **detectado automaticamente** pelo `pedido_id`. Opcionalmente, você pode informar o parâmetro `tipo` na query string para validação.

---

## 1. Adicionar Produto ao Pedido

Adiciona um produto, receita ou combo a um pedido existente. **Agora suporta complementos para todos os tipos de pedido** (Delivery, Balcão e Mesa).

### Endpoint
```
POST /api/pedidos/admin/{pedido_id}/itens?tipo=DELIVERY (opcional)
POST /api/pedidos/admin/{pedido_id}/itens?tipo=BALCAO (opcional)
POST /api/pedidos/admin/{pedido_id}/itens?tipo=MESA (opcional)
```

### Parâmetros de URL
- `pedido_id` (integer, obrigatório): ID do pedido
- `tipo` (string, opcional): Tipo de pedido (DELIVERY, BALCAO, MESA) - usado apenas para validação

### Body Request
```json
{
  "acao": "ADD",
  "tipo": "DELIVERY | BALCAO | MESA (opcional)",
  "produto_cod_barras": "string (opcional)",
  "receita_id": "integer (opcional)",
  "combo_id": "integer (opcional)",
  "quantidade": "integer (obrigatório, mínimo: 1)",
  "observacao": "string (opcional)",
  "complementos": [
    {
      "complemento_id": "integer",
      "adicionais": [
        {
          "adicional_id": "integer",
          "quantidade": "integer (padrão: 1, mínimo: 1)"
        }
      ]
    }
  ]
}
```

### Regras de Validação

1. **Identificação do Produto**: É necessário informar **exatamente um** dos seguintes campos:
   - `produto_cod_barras`: Para produtos simples
   - `receita_id`: Para receitas
   - `combo_id`: Para combos

2. **Complementos**: 
   - ✅ **Agora disponível para Delivery, Balcão e Mesa**
   - Cada complemento pode ter múltiplos adicionais
   - A quantidade do adicional é usada apenas se o complemento for quantitativo

3. **Tipo**: 
   - Opcional no body e na query string
   - Se informado, será validado contra o tipo real do pedido
   - Se não informado, será detectado automaticamente pelo `pedido_id`

4. **Quantidade**: 
   - Obrigatória
   - Valor mínimo: 1
   - Se não informada, será usada quantidade = 1

### Exemplos de Request

#### Adicionar Produto Simples com Complementos (Delivery)
```json
{
  "acao": "ADD",
  "produto_cod_barras": "7891234567890",
  "quantidade": 2,
  "observacao": "Sem cebola",
  "complementos": [
    {
      "complemento_id": 3,
      "adicionais": [
        {
          "adicional_id": 10,
          "quantidade": 2
        }
      ]
    }
  ]
}
```

#### Adicionar Receita com Complementos (Mesa/Balcão/Delivery)
```json
{
  "acao": "ADD",
  "receita_id": 15,
  "quantidade": 1,
  "observacao": "Bem passado",
  "complementos": [
    {
      "complemento_id": 3,
      "adicionais": [
        {
          "adicional_id": 10,
          "quantidade": 2
        },
        {
          "adicional_id": 11,
          "quantidade": 1
        }
      ]
    },
    {
      "complemento_id": 5,
      "adicionais": [
        {
          "adicional_id": 20,
          "quantidade": 1
        }
      ]
    }
  ]
}
```

#### Adicionar Combo com Complementos (Delivery)
```json
{
  "acao": "ADD",
  "combo_id": 7,
  "quantidade": 1,
  "tipo": "DELIVERY",
  "complementos": [
    {
      "complemento_id": 2,
      "adicionais": [
        {
          "adicional_id": 5,
          "quantidade": 1
        }
      ]
    }
  ]
}
```

### Response
```json
{
  "id": 123,
  "status": "P",
  "tipo_entrega": "DELIVERY",
  "valor_total": 45.90,
  "itens": [
    {
      "id": 456,
      "produto_cod_barras": "7891234567890",
      "quantidade": 2,
      "preco_unitario": 12.95,
      "preco_total": 25.90,
      "observacao": "Sem cebola"
    }
  ],
  // ... outros campos do pedido
}
```

### Status Codes
- `200 OK`: Produto adicionado com sucesso
- `400 Bad Request`: Dados inválidos (ex: pedido fechado, produto indisponível, múltiplos identificadores, tipo não corresponde)
- `404 Not Found`: Pedido ou produto não encontrado
- `403 Forbidden`: Sem permissão para acessar o pedido

---

## 2. Atualizar Item do Pedido

Atualiza a quantidade ou observação de um item existente no pedido.

### Endpoint
```
PATCH /api/pedidos/admin/{pedido_id}/itens/{item_id}
```

### Parâmetros de URL
- `pedido_id` (integer, obrigatório): ID do pedido
- `item_id` (integer, obrigatório): ID do item a ser atualizado

### Body Request
```json
{
  "acao": "UPDATE",
  "tipo": "DELIVERY | BALCAO | MESA (opcional)",
  "quantidade": "integer (opcional, mínimo: 1)",
  "observacao": "string (opcional)"
}
```

### Observações Importantes

⚠️ **Limitações por Tipo de Pedido:**
- **Delivery**: ✅ Suporta atualização completa (quantidade e observação)
- **Mesa**: ❌ **NÃO suporta** atualização parcial de itens. Use remover e adicionar novamente.
- **Balcão**: ❌ **NÃO suporta** atualização parcial de itens. Use remover e adicionar novamente.

### Exemplos de Request

#### Atualizar Quantidade (Delivery)
```json
{
  "acao": "UPDATE",
  "quantidade": 3
}
```

#### Atualizar Observação (Delivery)
```json
{
  "acao": "UPDATE",
  "observacao": "Sem cebola, sem tomate"
}
```

#### Atualizar Quantidade e Observação (Delivery)
```json
{
  "acao": "UPDATE",
  "quantidade": 2,
  "observacao": "Bem passado"
}
```

### Response
```json
{
  "id": 123,
  "status": "P",
  "tipo_entrega": "DELIVERY",
  "valor_total": 38.85,
  "itens": [
    {
      "id": 456,
      "produto_cod_barras": "7891234567890",
      "quantidade": 3,
      "preco_unitario": 12.95,
      "preco_total": 38.85,
      "observacao": "Sem cebola, sem tomate"
    }
  ],
  // ... outros campos do pedido
}
```

### Status Codes
- `200 OK`: Item atualizado com sucesso
- `400 Bad Request`: Dados inválidos ou tipo de pedido não suporta atualização
- `404 Not Found`: Pedido ou item não encontrado
- `403 Forbidden`: Sem permissão para acessar o pedido

---

## 3. Remover Item do Pedido

Remove um item específico do pedido.

### Endpoint
```
DELETE /api/pedidos/admin/{pedido_id}/itens/{item_id}
```

### Parâmetros de URL
- `pedido_id` (integer, obrigatório): ID do pedido
- `item_id` (integer, obrigatório): ID do item a ser removido

### Body Request
Não requer body.

### Exemplos de Request

#### Remover Item
```
DELETE /api/pedidos/admin/123/itens/456
```

### Response
```json
{
  "id": 123,
  "status": "P",
  "tipo_entrega": "DELIVERY",
  "valor_total": 12.95,
  "itens": [
    // Item removido não aparece mais na lista
  ],
  // ... outros campos do pedido
}
```

### Status Codes
- `200 OK`: Item removido com sucesso
- `400 Bad Request`: Pedido fechado ou cancelado
- `404 Not Found`: Pedido ou item não encontrado
- `403 Forbidden`: Sem permissão para acessar o pedido

---

## 4. Gerenciar Item (Endpoint Unificado)

Endpoint alternativo que aceita todas as ações (ADD, UPDATE, REMOVE) em um único endpoint.

### Endpoint
```
POST /api/pedidos/admin/{pedido_id}/itens?tipo=DELIVERY (opcional)
```

### Parâmetros de URL
- `pedido_id` (integer, obrigatório): ID do pedido
- `tipo` (string, opcional): Tipo de pedido para validação

### Body Request

#### Para Adicionar (acao: "ADD")
```json
{
  "acao": "ADD",
  "tipo": "DELIVERY | BALCAO | MESA (opcional)",
  "produto_cod_barras": "string (opcional)",
  "receita_id": "integer (opcional)",
  "combo_id": "integer (opcional)",
  "quantidade": "integer (obrigatório)",
  "observacao": "string (opcional)",
  "complementos": "array (opcional, suportado em todos os tipos)"
}
```

#### Para Atualizar (acao: "UPDATE")
```json
{
  "acao": "UPDATE",
  "tipo": "DELIVERY | BALCAO | MESA (opcional)",
  "item_id": "integer (obrigatório)",
  "quantidade": "integer (opcional)",
  "observacao": "string (opcional)"
}
```

#### Para Remover (acao: "REMOVE")
```json
{
  "acao": "REMOVE",
  "tipo": "DELIVERY | BALCAO | MESA (opcional)",
  "item_id": "integer (obrigatório)"
}
```

### Exemplos

#### Adicionar Produto com Complementos (Delivery)
```json
{
  "acao": "ADD",
  "produto_cod_barras": "7891234567890",
  "quantidade": 2,
  "observacao": "Sem cebola",
  "complementos": [
    {
      "complemento_id": 3,
      "adicionais": [
        { "adicional_id": 10, "quantidade": 2 }
      ]
    }
  ]
}
```

#### Atualizar Item (Delivery)
```json
{
  "acao": "UPDATE",
  "item_id": 456,
  "quantidade": 3,
  "observacao": "Bem passado"
}
```

#### Remover Item
```json
{
  "acao": "REMOVE",
  "item_id": 456
}
```

---

## Schema Completo - PedidoItemMutationRequest

```typescript
enum PedidoItemMutationAction {
  ADD = "ADD",
  UPDATE = "UPDATE",
  REMOVE = "REMOVE"
}

enum TipoEntregaEnum {
  DELIVERY = "DELIVERY",
  BALCAO = "BALCAO",
  MESA = "MESA",
  RETIRADA = "RETIRADA"
}

interface ItemAdicionalComplementoRequest {
  adicional_id: number;
  quantidade?: number; // padrão: 1, mínimo: 1
}

interface ItemComplementoRequest {
  complemento_id: number;
  adicionais: ItemAdicionalComplementoRequest[];
}

interface PedidoItemMutationRequest {
  acao: PedidoItemMutationAction;
  tipo?: TipoEntregaEnum; // opcional - detectado automaticamente se não informado
  item_id?: number; // obrigatório para UPDATE e REMOVE
  produto_cod_barras?: string; // obrigatório para ADD de produto simples
  receita_id?: number; // obrigatório para ADD de receita
  combo_id?: number; // obrigatório para ADD de combo
  quantidade?: number; // obrigatório para ADD, opcional para UPDATE (mínimo: 1)
  observacao?: string; // opcional
  complementos?: ItemComplementoRequest[]; // suportado em Delivery, Balcão e Mesa
}
```

---

## Resumo de Funcionalidades por Tipo de Pedido

| Funcionalidade | Delivery | Balcão | Mesa |
|---------------|----------|--------|------|
| Adicionar Produto Simples | ✅ | ✅ | ✅ |
| Adicionar Receita | ✅ | ✅ | ✅ |
| Adicionar Combo | ✅ | ✅ | ✅ |
| Adicionar com Complementos | ✅ **NOVO** | ✅ | ✅ |
| Atualizar Item (quantidade/observação) | ✅ | ❌ | ❌ |
| Remover Item | ✅ | ✅ | ✅ |

---

## Erros Comuns e Soluções

### Erro 404: "PUT /api/pedidos/admin/balcao/97/adicionar-produto-generico"
**Problema**: Endpoint antigo que não existe mais.

**Solução**: Use o endpoint unificado:
```
POST /api/pedidos/admin/97/itens
```

Com o body:
```json
{
  "acao": "ADD",
  "produto_cod_barras": "SEU_CODIGO_BARRAS",
  "quantidade": 1,
  "complementos": [...]
}
```

### Erro 400: "Tipo informado no payload não corresponde ao tipo do pedido"
**Problema**: O parâmetro `tipo` informado não corresponde ao tipo real do pedido.

**Solução**: 
1. Remova o parâmetro `tipo` (será detectado automaticamente), ou
2. Verifique o tipo correto do pedido e informe o valor correto

### Erro 400: "Atualização parcial de itens não suportada para balcão/mesa"
**Problema**: Tentativa de atualizar item em pedido de balcão ou mesa.

**Solução**: 
1. Remova o item antigo: `DELETE /api/pedidos/admin/{pedido_id}/itens/{item_id}`
2. Adicione o item novamente com os dados atualizados: `POST /api/pedidos/admin/{pedido_id}/itens` com `acao: "ADD"`

### Erro 400: "É necessário informar produto_cod_barras, receita_id ou combo_id"
**Problema**: Nenhum identificador de produto foi informado, ou múltiplos foram informados.

**Solução**: Informe exatamente um dos campos: `produto_cod_barras`, `receita_id` ou `combo_id`.

### Erro 400: "Pedido fechado/cancelado"
**Problema**: Tentativa de modificar pedido com status fechado (C) ou cancelado (E).

**Solução**: Verifique o status do pedido antes de tentar modificá-lo. Pedidos fechados ou cancelados não podem ser modificados.

---

## Exemplos de Uso Completo

### Fluxo: Adicionar Produto com Complementos (Delivery - NOVO)
```javascript
// 1. Adicionar produto com complementos em pedido de delivery
const response = await fetch('/api/pedidos/admin/123/itens?tipo=DELIVERY', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer SEU_TOKEN'
  },
  body: JSON.stringify({
    acao: 'ADD',
    produto_cod_barras: '7891234567890',
    quantidade: 2,
    observacao: 'Bem passado',
    complementos: [
      {
        complemento_id: 3,
        adicionais: [
          { adicional_id: 10, quantidade: 2 },
          { adicional_id: 11, quantidade: 1 }
        ]
      }
    ]
  })
});
```

### Fluxo: Adicionar Receita com Complementos (Mesa)
```javascript
// 1. Adicionar receita com complementos
const response = await fetch('/api/pedidos/admin/97/itens', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer SEU_TOKEN'
  },
  body: JSON.stringify({
    acao: 'ADD',
    receita_id: 15,
    quantidade: 1,
    observacao: 'Bem passado',
    complementos: [
      {
        complemento_id: 3,
        adicionais: [
          { adicional_id: 10, quantidade: 2 }
        ]
      }
    ]
  })
});
```

### Fluxo: Atualizar Item (Delivery)
```javascript
// 1. Atualizar quantidade e observação
const response = await fetch('/api/pedidos/admin/123/itens/456', {
  method: 'PATCH',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer SEU_TOKEN'
  },
  body: JSON.stringify({
    acao: 'UPDATE',
    quantidade: 3,
    observacao: 'Sem cebola, sem tomate'
  })
});
```

### Fluxo: Remover e Re-adicionar Item (Balcão/Mesa)
```javascript
// 1. Remover item antigo
await fetch('/api/pedidos/admin/97/itens/456', {
  method: 'DELETE',
  headers: {
    'Authorization': 'Bearer SEU_TOKEN'
  }
});

// 2. Adicionar item com dados atualizados
await fetch('/api/pedidos/admin/97/itens', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer SEU_TOKEN'
  },
  body: JSON.stringify({
    acao: 'ADD',
    produto_cod_barras: '7891234567890',
    quantidade: 5, // nova quantidade
    observacao: 'Nova observação',
    complementos: [
      // novos complementos
    ]
  })
});
```

---

## Notas Importantes

1. **Complementos**: ✅ **Agora suportado para Delivery, Balcão e Mesa**

2. **Tipo de Pedido**: 
   - O tipo é detectado automaticamente pelo `pedido_id`
   - O parâmetro `tipo` é opcional e serve apenas para validação
   - Se informado e não corresponder ao tipo real do pedido, retornará erro 400

3. **Atualização de Itens**: 
   - Delivery: ✅ Suporta atualização parcial via PATCH
   - Mesa/Balcão: ❌ Não suporta atualização parcial. Use remover + adicionar.

4. **Validações Automáticas**:
   - Produto deve estar disponível
   - Produto deve pertencer à empresa do pedido
   - Pedido não pode estar fechado ou cancelado
   - Quantidade mínima: 1
   - Tipo informado (se houver) deve corresponder ao tipo do pedido

5. **Recálculo Automático**: Todos os endpoints recalculam automaticamente o valor total do pedido após a operação.

6. **Histórico**: Todas as operações são registradas no histórico do pedido para auditoria.

7. **Endpoint Unificado**: Todos os tipos de pedido usam o mesmo endpoint. Não há mais endpoints separados por tipo.

---

## Migração de Código Antigo

Se você estava usando endpoints antigos separados por tipo, migre para o endpoint unificado:

### Antes (DEPRECADO)
```
PUT /api/pedidos/admin/balcao/97/adicionar-produto-generico
PUT /api/pedidos/admin/mesa/97/adicionar-produto-generico
```

### Agora (UNIFICADO)
```
POST /api/pedidos/admin/97/itens
```

Com o body:
```json
{
  "acao": "ADD",
  "produto_cod_barras": "...",
  "quantidade": 1,
  "complementos": [...]
}
```

---

## Suporte

Para dúvidas ou problemas, consulte a documentação da API ou entre em contato com a equipe de desenvolvimento.
