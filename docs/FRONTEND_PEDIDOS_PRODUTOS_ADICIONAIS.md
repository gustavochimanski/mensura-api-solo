# 📋 Documentação Frontend - Estrutura Unificada de Produtos/Adicionais em Pedidos

## 🎯 Visão Geral

Todos os pedidos (DELIVERY, MESA, BALCÃO) agora usam a **mesma estrutura unificada** de produtos, com suporte a:
- ✅ **Produtos normais** (código de barras)
- ✅ **Receitas**
- ✅ **Combos**
- ✅ **Adicionais** (dentro de cada item/receita/combo)

---

## 📦 1. ESTRUTURAS DE DADOS

### 1.1. Request - Adicionar Adicional a um Item

```typescript
interface ItemAdicionalRequest {
  adicional_id: number;      // ID do adicional
  quantidade: number;         // Quantidade do adicional (padrão: 1)
}
```

### 1.2. Request - Item de Produto

```typescript
interface ItemPedidoRequest {
  produto_cod_barras: string;
  quantidade: number;
  observacao?: string;
  
  // NOVO: Adicionais com quantidade
  adicionais?: ItemAdicionalRequest[];
  
  // LEGADO: Ainda aceito, mas não recomendado
  adicionais_ids?: number[];  // Quantidade implícita = 1
}
```

### 1.3. Request - Receita

```typescript
interface ReceitaPedidoRequest {
  receita_id: number;
  quantidade: number;
  observacao?: string;
  
  // NOVO: Adicionais com quantidade
  adicionais?: ItemAdicionalRequest[];
  
  // LEGADO: Ainda aceito
  adicionais_ids?: number[];
}
```

### 1.4. Request - Combo

```typescript
interface ComboPedidoRequest {
  combo_id: number;
  quantidade: number;
  
  // NOVO: Adicionais com quantidade
  adicionais?: ItemAdicionalRequest[];
}
```

### 1.5. Request - Objeto Produtos (Agrupado)

```typescript
interface ProdutosPedidoRequest {
  itens: ItemPedidoRequest[];           // Produtos normais
  receitas?: ReceitaPedidoRequest[];    // Receitas (opcional)
  combos?: ComboPedidoRequest[];        // Combos (opcional)
}
```

### 1.6. Response - Adicional do Pedido

```typescript
interface ProdutoPedidoAdicionalOut {
  adicional_id?: number;
  nome?: string;
  quantidade: number;
  preco_unitario: number;
  total: number;
}
```

### 1.7. Response - Item de Produto

```typescript
interface ProdutoPedidoItemOut {
  item_id?: number;
  produto_cod_barras?: string;
  descricao?: string;
  imagem?: string;
  quantidade: number;
  preco_unitario: number;
  observacao?: string;
  adicionais: ProdutoPedidoAdicionalOut[];  // Adicionais do item
}
```

### 1.8. Response - Receita

```typescript
interface ReceitaPedidoOut {
  item_id?: number;
  receita_id: number;
  nome?: string;
  quantidade: number;
  preco_unitario: number;
  observacao?: string;
  adicionais: ProdutoPedidoAdicionalOut[];  // Adicionais da receita
}
```

### 1.9. Response - Combo

```typescript
interface ComboPedidoOut {
  combo_id: number;
  nome?: string;
  quantidade: number;
  preco_unitario: number;
  observacao?: string;
  adicionais: ProdutoPedidoAdicionalOut[];  // Adicionais do combo
}
```

### 1.10. Response - Objeto Produtos (Agrupado)

```typescript
interface ProdutosPedidoOut {
  itens: ProdutoPedidoItemOut[];
  receitas: ReceitaPedidoOut[];
  combos: ComboPedidoOut[];
}
```

---

## 🔌 2. REQUESTS (ENTRADAS) - O QUE MUDOU

### 2.1. DELIVERY - Criar Pedido

**Endpoint:** `POST /api/cardapio/client/pedidos/checkout`

**Body (já estava assim, mantido):**

```json
{
  "empresa_id": 1,
  "endereco_id": 10,
  "tipo_pedido": "DELIVERY",
  "tipo_entrega": "DELIVERY",
  "observacao_geral": "obs do pedido",
  "cupom_id": null,
  "meios_pagamento": [
    { "id": 1, "valor": 50.00 }
  ],
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "789123",
        "quantidade": 2,
        "observacao": "sem cebola",
        "adicionais": [
          { "adicional_id": 10, "quantidade": 1 },
          { "adicional_id": 11, "quantidade": 2 }
        ]
      }
    ],
    "receitas": [
      {
        "receita_id": 5,
        "quantidade": 1,
        "observacao": "bem passado",
        "adicionais": [
          { "adicional_id": 32, "quantidade": 1 }
        ]
      }
    ],
    "combos": [
      {
        "combo_id": 3,
        "quantidade": 1,
        "adicionais": [
          { "adicional_id": 40, "quantidade": 1 }
        ]
      }
    ]
  }
}
```

**✅ Sem mudanças** - Já estava usando `produtos` corretamente.

---

### 2.2. MESA - Criar Pedido

**Endpoint:** `POST /api/mesas/admin/pedidos`

**Body (NOVO formato):**

```json
{
  "empresa_id": 1,
  "mesa_id": 12,
  "cliente_id": 123,
  "observacoes": "obs gerais da mesa",
  "num_pessoas": 4,
  
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "789123",
        "quantidade": 2,
        "observacao": "sem cebola",
        "adicionais": [
          { "adicional_id": 10, "quantidade": 1 }
        ]
      }
    ],
    "receitas": [
      {
        "receita_id": 5,
        "quantidade": 1,
        "adicionais": []
      }
    ],
    "combos": [
      {
        "combo_id": 3,
        "quantidade": 1,
        "adicionais": []
      }
    ]
  }
  
  // LEGADO: Ainda aceito, mas não recomendado
  // "itens": [ { "produto_cod_barras": "789...", "quantidade": 1 } ]
}
```

**Mudanças:**
- ✅ **NOVO:** Campo `produtos` (obrigatório no fluxo novo)
- ✅ **NOVO:** Suporte a `receitas` e `combos`
- ✅ **NOVO:** Adicionais dentro de cada item/receita/combo
- ⚠️ **LEGADO:** Campo `itens` ainda aceito, mas será descontinuado

---

### 2.3. BALCÃO - Criar Pedido

**Endpoint:** `POST /api/balcao/admin/pedidos`

**Body (NOVO formato):**

```json
{
  "empresa_id": 1,
  "mesa_id": null,
  "cliente_id": 123,
  "observacoes": "para viagem",
  
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "789123",
        "quantidade": 1,
        "observacao": "sem gelo",
        "adicionais": [
          { "adicional_id": 10, "quantidade": 2 }
        ]
      }
    ],
    "receitas": [],
    "combos": []
  }
}
```

**Mudanças:**
- ✅ **NOVO:** Campo `produtos` (obrigatório no fluxo novo)
- ✅ **NOVO:** Suporte a `receitas` e `combos`
- ✅ **NOVO:** Adicionais dentro de cada item

---

### 2.4. MESA/BALCÃO - Adicionar Item

**Endpoints:**
- `POST /api/mesas/admin/pedidos/{pedido_id}/itens`
- `POST /api/balcao/admin/pedidos/{pedido_id}/itens`

**Body (NOVO formato):**

```json
{
  "produto_cod_barras": "789123",
  "quantidade": 1,
  "observacao": "sem gelo",
  
  // NOVO: Adicionais com quantidade
  "adicionais": [
    { "adicional_id": 10, "quantidade": 2 },
    { "adicional_id": 11, "quantidade": 1 }
  ],
  
  // LEGADO: Ainda aceito
  "adicionais_ids": [ 99 ]
}
```

**Mudanças:**
- ✅ **NOVO:** Campo `adicionais` (array de objetos com `adicional_id` e `quantidade`)
- ⚠️ **LEGADO:** Campo `adicionais_ids` ainda aceito, mas quantidade implícita = 1

---

## 📤 3. RESPONSES (SAÍDAS) - O QUE MUDOU

### 3.1. DELIVERY - Buscar Pedido

**Endpoints:**
- `GET /api/cardapio/admin/pedidos/{pedido_id}`
- `GET /api/cardapio/client/pedidos/{pedido_id}`

**Response (NOVO formato):**

```json
{
  "id": 123,
  "status": "R",
  "empresa_id": 1,
  "valor_total": 75.0,
  "observacao_geral": "obs gerais",
  
  // NOVO: Objeto produtos estruturado
  "produtos": {
    "itens": [
      {
        "item_id": 1,
        "produto_cod_barras": "789123",
        "descricao": "X-Burger",
        "imagem": "https://...",
        "quantidade": 2,
        "preco_unitario": 20.0,
        "observacao": "sem cebola",
        "adicionais": [
          {
            "adicional_id": 10,
            "nome": "Bacon extra",
            "quantidade": 1,
            "preco_unitario": 5.0,
            "total": 5.0
          }
        ]
      }
    ],
    "receitas": [
      {
        "item_id": 2,
        "receita_id": 5,
        "nome": "Pizza meia calabresa",
        "quantidade": 1,
        "preco_unitario": 30.0,
        "observacao": null,
        "adicionais": []
      }
    ],
    "combos": [
      {
        "combo_id": 3,
        "nome": "Combo X-Burger + Refri",
        "quantidade": 1,
        "preco_unitario": 35.0,
        "observacao": null,
        "adicionais": []
      }
    ]
  },
  
  // LEGADO: Mantido para compatibilidade (ignorar no front novo)
  "itens": [
    {
      "id": 1,
      "produto_cod_barras": "789123",
      "quantidade": 2,
      "preco_unitario": 20.0,
      "observacao": "sem cebola"
    }
  ]
}
```

**Mudanças:**
- ✅ **NOVO:** Campo `produtos` com estrutura completa (itens/receitas/combos)
- ✅ **NOVO:** Adicionais dentro de cada item/receita/combo
- ⚠️ **LEGADO:** Campo `itens` mantido, mas **não usar** no front novo

---

### 3.2. MESA - Buscar Pedido

**Endpoint:** `GET /api/mesas/admin/pedidos/{pedido_id}`

**Response (NOVO formato):**

```json
{
  "id": 123,
  "numero_pedido": "M12-001",
  "empresa_id": 1,
  "mesa_id": 12,
  "status": "R",
  "status_descricao": "EM PREPARO",
  "valor_total": 75.0,
  "observacoes": "obs gerais",
  
  // NOVO: Objeto produtos estruturado
  "produtos": {
    "itens": [
      {
        "item_id": 1,
        "produto_cod_barras": "789123",
        "descricao": "X-Burger",
        "quantidade": 2,
        "preco_unitario": 20.0,
        "observacao": "sem cebola",
        "adicionais": [
          {
            "adicional_id": 10,
            "nome": "Bacon extra",
            "quantidade": 1,
            "preco_unitario": 5.0,
            "total": 5.0
          }
        ]
      }
    ],
    "receitas": [],
    "combos": []
  },
  
  // LEGADO: Mantido para compatibilidade
  "itens": [
    {
      "id": 1,
      "produto_cod_barras": "789123",
      "quantidade": 2,
      "preco_unitario": 20.0
    }
  ]
}
```

**Mudanças:**
- ✅ **NOVO:** Campo `produtos` com estrutura completa
- ✅ **NOVO:** Adicionais dentro de cada item
- ⚠️ **LEGADO:** Campo `itens` mantido, mas **não usar** no front novo

---

### 3.3. BALCÃO - Buscar Pedido

**Endpoint:** `GET /api/balcao/admin/pedidos/{pedido_id}`

**Response (NOVO formato):**

```json
{
  "id": 123,
  "numero_pedido": "BAL-000123",
  "empresa_id": 1,
  "mesa_id": null,
  "status": "R",
  "status_descricao": "EM PREPARO",
  "valor_total": 50.0,
  "observacoes": "para viagem",
  
  // NOVO: Objeto produtos estruturado
  "produtos": {
    "itens": [
      {
        "item_id": 1,
        "produto_cod_barras": "789123",
        "descricao": "X-Burger",
        "quantidade": 1,
        "preco_unitario": 20.0,
        "observacao": "sem gelo",
        "adicionais": [
          {
            "adicional_id": 10,
            "nome": "Bacon extra",
            "quantidade": 2,
            "preco_unitario": 5.0,
            "total": 10.0
          }
        ]
      }
    ],
    "receitas": [],
    "combos": []
  },
  
  // LEGADO: Mantido para compatibilidade
  "itens": [...]
}
```

**Mudanças:**
- ✅ **NOVO:** Campo `produtos` com estrutura completa
- ✅ **NOVO:** Adicionais dentro de cada item
- ⚠️ **LEGADO:** Campo `itens` mantido, mas **não usar** no front novo

---

## 📋 4. ENDPOINTS AFETADOS

### 4.1. DELIVERY

| Endpoint | Método | Mudança |
|----------|--------|---------|
| `/api/cardapio/client/pedidos/checkout` | POST | ✅ Já estava correto (usa `produtos`) |
| `/api/cardapio/admin/pedidos/{id}` | GET | ✅ **NOVO:** Retorna `produtos` estruturado |
| `/api/cardapio/client/pedidos/{id}` | GET | ✅ **NOVO:** Retorna `produtos` estruturado |

### 4.2. MESA

| Endpoint | Método | Mudança |
|----------|--------|---------|
| `/api/mesas/admin/pedidos` | POST | ✅ **NOVO:** Aceita `produtos` (itens/receitas/combos) |
| `/api/mesas/admin/pedidos/{id}` | GET | ✅ **NOVO:** Retorna `produtos` estruturado |
| `/api/mesas/admin/pedidos/{id}/itens` | POST | ✅ **NOVO:** Aceita `adicionais` no body |

### 4.3. BALCÃO

| Endpoint | Método | Mudança |
|----------|--------|---------|
| `/api/balcao/admin/pedidos` | POST | ✅ **NOVO:** Aceita `produtos` (itens/receitas/combos) |
| `/api/balcao/admin/pedidos/{id}` | GET | ✅ **NOVO:** Retorna `produtos` estruturado |
| `/api/balcao/admin/pedidos/{id}/itens` | POST | ✅ **NOVO:** Aceita `adicionais` no body |

---

## 💻 5. EXEMPLOS PRÁTICOS PARA O FRONTEND

### 5.1. Criar Pedido de Mesa com Produtos e Adicionais

```typescript
const criarPedidoMesa = async (dados: {
  empresaId: number;
  mesaId: number;
  clienteId?: number;
  produtos: {
    itens: Array<{
      produtoCodBarras: string;
      quantidade: number;
      observacao?: string;
      adicionais?: Array<{
        adicionalId: number;
        quantidade: number;
      }>;
    }>;
    receitas?: Array<{
      receitaId: number;
      quantidade: number;
      observacao?: string;
      adicionais?: Array<{
        adicionalId: number;
        quantidade: number;
      }>;
    }>;
    combos?: Array<{
      comboId: number;
      quantidade: number;
      adicionais?: Array<{
        adicionalId: number;
        quantidade: number;
      }>;
    }>;
  };
}) => {
  const response = await fetch('/api/mesas/admin/pedidos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      empresa_id: dados.empresaId,
      mesa_id: dados.mesaId,
      cliente_id: dados.clienteId,
      produtos: dados.produtos,
    }),
  });
  return response.json();
};

// Uso:
await criarPedidoMesa({
  empresaId: 1,
  mesaId: 12,
  clienteId: 123,
  produtos: {
    itens: [
      {
        produtoCodBarras: '789123',
        quantidade: 2,
        observacao: 'sem cebola',
        adicionais: [
          { adicionalId: 10, quantidade: 1 },
          { adicionalId: 11, quantidade: 2 },
        ],
      },
    ],
    receitas: [
      {
        receitaId: 5,
        quantidade: 1,
        adicionais: [{ adicionalId: 32, quantidade: 1 }],
      },
    ],
    combos: [
      {
        comboId: 3,
        quantidade: 1,
        adicionais: [],
      },
    ],
  },
});
```

### 5.2. Adicionar Item com Adicionais

```typescript
const adicionarItemMesa = async (
  pedidoId: number,
  item: {
    produtoCodBarras: string;
    quantidade: number;
    observacao?: string;
    adicionais?: Array<{
      adicionalId: number;
      quantidade: number;
    }>;
  }
) => {
  const response = await fetch(`/api/mesas/admin/pedidos/${pedidoId}/itens`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      produto_cod_barras: item.produtoCodBarras,
      quantidade: item.quantidade,
      observacao: item.observacao,
      adicionais: item.adicionais,
    }),
  });
  return response.json();
};

// Uso:
await adicionarItemMesa(123, {
  produtoCodBarras: '789123',
  quantidade: 1,
  observacao: 'sem gelo',
  adicionais: [
    { adicionalId: 10, quantidade: 2 },
  ],
});
```

### 5.3. Buscar Pedido e Usar Estrutura de Produtos

```typescript
const buscarPedidoMesa = async (pedidoId: number) => {
  const response = await fetch(`/api/mesas/admin/pedidos/${pedidoId}`);
  const pedido = await response.json();
  
  // ✅ USAR: Estrutura nova (produtos)
  const { produtos } = pedido;
  
  // Itens normais
  produtos.itens.forEach((item) => {
    console.log(`Item: ${item.descricao}, Qtd: ${item.quantidade}`);
    item.adicionais.forEach((adicional) => {
      console.log(`  - ${adicional.nome} (x${adicional.quantidade}): R$ ${adicional.total}`);
    });
  });
  
  // Receitas
  produtos.receitas.forEach((receita) => {
    console.log(`Receita: ${receita.nome}, Qtd: ${receita.quantidade}`);
  });
  
  // Combos
  produtos.combos.forEach((combo) => {
    console.log(`Combo: ${combo.nome}, Qtd: ${combo.quantidade}`);
  });
  
  // ❌ NÃO USAR: Campo legado (itens)
  // pedido.itens // Ignorar este campo
  
  return pedido;
};
```

### 5.4. Calcular Total com Adicionais

```typescript
const calcularTotalPedido = (pedido: {
  produtos: {
    itens: Array<{
      quantidade: number;
      preco_unitario: number;
      adicionais: Array<{
        total: number;
      }>;
    }>;
    receitas: Array<{
      quantidade: number;
      preco_unitario: number;
      adicionais: Array<{
        total: number;
      }>;
    }>;
    combos: Array<{
      quantidade: number;
      preco_unitario: number;
      adicionais: Array<{
        total: number;
      }>;
    }>;
  };
}) => {
  let total = 0;
  
  // Itens
  pedido.produtos.itens.forEach((item) => {
    total += item.quantidade * item.preco_unitario;
    item.adicionais.forEach((adicional) => {
      total += adicional.total;
    });
  });
  
  // Receitas
  pedido.produtos.receitas.forEach((receita) => {
    total += receita.quantidade * receita.preco_unitario;
    receita.adicionais.forEach((adicional) => {
      total += adicional.total;
    });
  });
  
  // Combos
  pedido.produtos.combos.forEach((combo) => {
    total += combo.quantidade * combo.preco_unitario;
    combo.adicionais.forEach((adicional) => {
      total += adicional.total;
    });
  });
  
  return total;
};
```

---

## ⚠️ 6. MIGRAÇÃO DO CÓDIGO LEGADO

### 6.1. Antes (Código Antigo)

```typescript
// ❌ NÃO USAR MAIS
const criarPedidoMesa = {
  empresa_id: 1,
  mesa_id: 12,
  itens: [
    { produto_cod_barras: '789123', quantidade: 1 },
  ],
};
```

### 6.2. Depois (Código Novo)

```typescript
// ✅ USAR AGORA
const criarPedidoMesa = {
  empresa_id: 1,
  mesa_id: 12,
  produtos: {
    itens: [
      {
        produto_cod_barras: '789123',
        quantidade: 1,
        adicionais: [
          { adicional_id: 10, quantidade: 1 },
        ],
      },
    ],
  },
};
```

### 6.3. Antes (Ler Pedido)

```typescript
// ❌ NÃO USAR MAIS
pedido.itens.forEach((item) => {
  console.log(item.produto_cod_barras);
});
```

### 6.4. Depois (Ler Pedido)

```typescript
// ✅ USAR AGORA
pedido.produtos.itens.forEach((item) => {
  console.log(item.descricao);
  item.adicionais.forEach((adicional) => {
    console.log(adicional.nome);
  });
});
```

---

## 📝 7. CHECKLIST DE IMPLEMENTAÇÃO

### 7.1. Requests (Envio)

- [ ] Atualizar criação de pedido de **MESA** para usar `produtos`
- [ ] Atualizar criação de pedido de **BALCÃO** para usar `produtos`
- [ ] Atualizar adicionar item (MESA/BALCÃO) para usar `adicionais` (array de objetos)
- [ ] Remover uso de `itens` direto na raiz (usar `produtos.itens`)
- [ ] Remover uso de `adicionais_ids` (usar `adicionais` com quantidade)

### 7.2. Responses (Leitura)

- [ ] Atualizar leitura de pedido **DELIVERY** para usar `produtos`
- [ ] Atualizar leitura de pedido **MESA** para usar `produtos`
- [ ] Atualizar leitura de pedido **BALCÃO** para usar `produtos`
- [ ] Ignorar campo `itens` legado nas respostas
- [ ] Atualizar componentes de exibição para mostrar `produtos.itens/receitas/combos`
- [ ] Atualizar componentes para exibir adicionais dentro de cada item

### 7.3. Cálculos

- [ ] Atualizar cálculo de totais para considerar `produtos`
- [ ] Atualizar cálculo de totais para incluir adicionais de cada item
- [ ] Atualizar exibição de valores para mostrar adicionais separadamente

---

## 🎯 8. RESUMO DAS MUDANÇAS

| Aspecto | Antes | Agora |
|---------|-------|-------|
| **Estrutura** | `itens` direto na raiz | `produtos.itens/receitas/combos` |
| **Adicionais** | `adicionais_ids` (array de números) | `adicionais` (array de objetos com quantidade) |
| **Receitas** | ❌ Não suportado em mesa/balcão | ✅ Suportado via `produtos.receitas` |
| **Combos** | ❌ Não suportado em mesa/balcão | ✅ Suportado via `produtos.combos` |
| **Response** | Apenas `itens` flat | `produtos` estruturado + `itens` legado |

---

## 📌 9. OBSERVAÇÕES IMPORTANTES

1. **Campo `itens` legado:** Mantido nas respostas apenas para compatibilidade. **Não usar** no front novo.

2. **Campo `adicionais_ids` legado:** Ainda aceito nos requests, mas quantidade implícita = 1. **Migrar** para `adicionais` com quantidade explícita.

3. **Kanban:** **NÃO foi alterado** - continua como antes, sem campo `produtos`.

4. **Delivery:** Já estava usando `produtos` corretamente, apenas as **responses** foram atualizadas para incluir a estrutura completa.

5. **Adicionais:** Sempre ficam **dentro** do item/receita/combo correspondente, nunca soltos no nível do pedido.

---

**Última atualização:** 2025-01-XX

