# Documentação: Adicionar Produtos em Pedidos (Balcão, Mesa e Delivery)

## Índice
1. [Visão Geral](#visão-geral)
2. [Tipos de Produtos](#tipos-de-produtos)
3. [Estrutura de Dados](#estrutura-de-dados)
4. [Endpoints](#endpoints)
5. [Fluxos de Adição](#fluxos-de-adição)
6. [Exemplos Práticos](#exemplos-práticos)
7. [Respostas da API](#respostas-da-api)

---

## Visão Geral

O sistema suporta três tipos de pedidos:
- **DELIVERY**: Pedidos para entrega
- **MESA**: Pedidos em mesas do estabelecimento
- **BALCAO**: Pedidos no balcão (retirada)

Todos os tipos de pedidos suportam três categorias de produtos:
1. **Itens Normais**: Produtos com código de barras
2. **Receitas**: Produtos compostos (sem código de barras próprio)
3. **Combos**: Conjuntos de produtos com preço especial

Cada produto pode ter **adicionais** vinculados, que são produtos extras que podem ser adicionados ao item principal.

---

## Tipos de Produtos

### 1. Itens Normais (Produtos com Código de Barras)

Produtos simples identificados por código de barras.

**Características:**
- Identificado por `produto_cod_barras`
- Possui preço unitário
- Pode ter adicionais vinculados
- Quantidade configurável

### 2. Receitas

Produtos compostos que não possuem código de barras próprio, mas são identificados por `receita_id`.

**Características:**
- Identificado por `receita_id` (não usa código de barras)
- Possui preço de venda próprio
- Pode ter adicionais vinculados diretamente à receita
- Quantidade configurável
- Pertence a uma empresa específica

### 3. Combos

Conjuntos de produtos vendidos como um pacote com preço especial.

**Características:**
- Identificado por `combo_id`
- Possui preço total (não unitário por item)
- Os itens do combo são distribuídos proporcionalmente no pedido
- Pode ter adicionais aplicados ao combo inteiro
- Quantidade configurável
- Pertence a uma empresa específica

### 4. Adicionais

Produtos extras que podem ser vinculados a:
- Itens normais (por código de barras)
- Receitas (por receita_id)
- Combos (aplicados ao combo inteiro)

**Características:**
- Identificado por `adicional_id`
- Possui preço unitário
- Quantidade configurável por adicional
- Multiplicado pela quantidade do item principal

---

## Estrutura de Dados

### Schema de Request (FinalizarPedidoRequest)

```typescript
{
  empresa_id?: number;              // Obrigatório para MESA e BALCAO
  endereco_id?: number;             // Obrigatório para DELIVERY
  tipo_pedido: "DELIVERY" | "MESA" | "BALCAO";
  tipo_entrega: "DELIVERY" | "RETIRADA";
  mesa_codigo?: string;             // Obrigatório para MESA
  num_pessoas?: number;             // Opcional para MESA (1-50)
  observacao_geral?: string;
  cupom_id?: number;
  troco_para?: number;
  meios_pagamento?: Array<{
    id?: number;                    // Novo formato
    meio_pagamento_id?: number;     // Legado
    valor: number;
  }>;
  
  // NOVO FORMATO (RECOMENDADO)
  produtos?: {
    itens?: Array<ItemPedidoRequest>;
    receitas?: Array<ReceitaPedidoRequest>;
    combos?: Array<ComboPedidoRequest>;
  };
  
  // FORMATO LEGADO (ainda suportado)
  itens?: Array<ItemPedidoRequest>;
  receitas?: Array<ReceitaPedidoRequest>;
  combos?: Array<ComboPedidoRequest>;
}
```

### ItemPedidoRequest (Item Normal)

```typescript
{
  produto_cod_barras: string;        // Obrigatório
  quantidade: number;               // >= 1
  observacao?: string;              // Opcional, max 255 chars
  
  // NOVO FORMATO (RECOMENDADO)
  adicionais?: Array<{
    adicional_id: number;
    quantidade: number;             // >= 1, padrão: 1
  }>;
  
  // FORMATO LEGADO (ainda suportado)
  adicionais_ids?: number[];        // Quantidade implícita = 1
}
```

### ReceitaPedidoRequest

```typescript
{
  receita_id: number;               // Obrigatório
  quantidade: number;               // >= 1
  observacao?: string;              // Opcional
  
  // NOVO FORMATO (RECOMENDADO)
  adicionais?: Array<{
    adicional_id: number;
    quantidade: number;             // >= 1, padrão: 1
  }>;
  
  // FORMATO LEGADO (ainda suportado)
  adicionais_ids?: number[];        // Quantidade implícita = 1
}
```

### ComboPedidoRequest

```typescript
{
  combo_id: number;                  // Obrigatório
  quantidade: number;               // >= 1, padrão: 1
  
  // Adicionais aplicados ao combo inteiro
  adicionais?: Array<{
    adicional_id: number;
    quantidade: number;             // >= 1, padrão: 1
  }>;
}
```

---

## Endpoints

### 1. Preview do Checkout (Sem Criar Pedido)

**Endpoint:** `POST /api/cardapio/client/pedidos/checkout/preview`

**Descrição:** Calcula o preview do checkout (subtotal, taxas, desconto, total) sem criar o pedido no banco de dados.

**Request Body:** `FinalizarPedidoRequest`

**Response:** `PreviewCheckoutResponse`

```typescript
{
  subtotal: number;
  taxa_entrega: number;
  taxa_servico: number;
  valor_total: number;
  desconto: number;
  distancia_km?: number;
  empresa_id?: number;
  tempo_entrega_minutos?: number;
}
```

### 2. Finalizar Checkout (Criar Pedido)

**Endpoint:** `POST /api/cardapio/client/pedidos/checkout`

**Descrição:** Finaliza o checkout criando o pedido no banco de dados.

**Request Body:** `FinalizarPedidoRequest`

**Response:** `PedidoResponse | PedidoMesaOut | PedidoBalcaoOut`

O tipo de resposta depende do `tipo_pedido`:
- `DELIVERY` → `PedidoResponse`
- `MESA` → `PedidoMesaOut`
- `BALCAO` → `PedidoBalcaoOut`

### 3. Adicionar Item a Pedido Existente (Delivery)

**Endpoint:** `PUT /api/cardapio/client/pedidos/{pedido_id}/itens`

**Descrição:** Adiciona, atualiza ou remove itens de um pedido de delivery existente.

**Request Body:** `ItemPedidoEditar`

```typescript
{
  id?: number;                      // Para atualizar/remover
  produto_cod_barras?: string;      // Para adicionar
  quantidade?: number;
  observacao?: string;
  acao: "novo-item" | "atualizar" | "remover";
}
```

**Response:** `PedidoResponse`

### 4. Adicionar Produto Genérico a Pedido de Mesa (NOVO - RECOMENDADO)

**Endpoint:** `POST /api/mesas/admin/pedidos/{pedido_id}/produtos`

**Descrição:** Adiciona qualquer tipo de produto (produto normal, receita ou combo) ao pedido. O sistema identifica automaticamente o tipo.

**Request Body:** `AdicionarProdutoGenericoRequest`

```typescript
{
  // Apenas um dos campos abaixo deve ser informado:
  produto_cod_barras?: string;  // Para produtos normais
  receita_id?: number;          // Para receitas
  combo_id?: number;            // Para combos
  
  quantidade: number;           // >= 1
  observacao?: string;
  adicionais?: Array<{
    adicional_id: number;
    quantidade: number;        // >= 1
  }>;
  adicionais_ids?: number[];    // LEGADO
}
```

**Response:** `PedidoMesaOut`

### 5. Adicionar Produto Genérico a Pedido de Balcão (NOVO - RECOMENDADO)

**Endpoint:** `POST /api/balcao/admin/pedidos/{pedido_id}/produtos`

**Descrição:** Adiciona qualquer tipo de produto (produto normal, receita ou combo) ao pedido. O sistema identifica automaticamente o tipo.

**Request Body:** `AdicionarProdutoGenericoRequest` (mesmo formato acima)

**Response:** `PedidoBalcaoOut`

### 6. Adicionar Item a Pedido de Mesa (LEGADO)

**Endpoint:** `POST /api/mesas/admin/pedidos/{pedido_id}/itens`

**⚠️ LEGADO:** Use o endpoint `/produtos` ao invés deste.

**Request Body:** `AdicionarItemRequest` (apenas produtos normais)

**Response:** `PedidoMesaOut`

### 7. Adicionar Item a Pedido de Balcão (LEGADO)

**Endpoint:** `POST /api/balcao/admin/pedidos/{pedido_id}/itens`

**⚠️ LEGADO:** Use o endpoint `/produtos` ao invés deste.

**Request Body:** `AdicionarItemRequest` (apenas produtos normais)

**Response:** `PedidoBalcaoOut`

---

## Fluxos de Adição

### Fluxo 1: Criar Pedido Completo (Checkout)

1. **Cliente monta o carrinho** com itens, receitas e combos
2. **Chama preview** para ver valores antes de finalizar
3. **Finaliza checkout** criando o pedido

**Exemplo de Request:**

```json
{
  "empresa_id": 1,
  "tipo_pedido": "MESA",
  "mesa_codigo": "5",
  "num_pessoas": 4,
  "observacao_geral": "Sem cebola",
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "7891234567890",
        "quantidade": 2,
        "observacao": "Bem passado",
        "adicionais": [
          {
            "adicional_id": 10,
            "quantidade": 2
          },
          {
            "adicional_id": 15,
            "quantidade": 1
          }
        ]
      }
    ],
    "receitas": [
      {
        "receita_id": 5,
        "quantidade": 1,
        "observacao": "Sem pimenta",
        "adicionais": [
          {
            "adicional_id": 20,
            "quantidade": 1
          }
        ]
      }
    ],
    "combos": [
      {
        "combo_id": 3,
        "quantidade": 2,
        "adicionais": [
          {
            "adicional_id": 25,
            "quantidade": 1
          }
        ]
      }
    ]
  }
}
```

### Fluxo 2: Adicionar Produto Genérico a Pedido Existente (RECOMENDADO)

**Para Mesa (Produto Normal):**

```json
POST /api/mesas/admin/pedidos/123/produtos
{
  "produto_cod_barras": "7891234567890",
  "quantidade": 1,
  "observacao": "Bem passado",
  "adicionais": [
    {
      "adicional_id": 10,
      "quantidade": 2
    }
  ]
}
```

**Para Mesa (Receita):**

```json
POST /api/mesas/admin/pedidos/123/produtos
{
  "receita_id": 5,
  "quantidade": 1,
  "observacao": "Sem pimenta",
  "adicionais": [
    {
      "adicional_id": 20,
      "quantidade": 2
    }
  ]
}
```

**Para Mesa (Combo):**

```json
POST /api/mesas/admin/pedidos/123/produtos
{
  "combo_id": 3,
  "quantidade": 2,
  "adicionais": [
    {
      "adicional_id": 25,
      "quantidade": 1
    }
  ]
}
```

**Para Balcão (mesmos exemplos, apenas trocar o endpoint):**

```json
POST /api/balcao/admin/pedidos/123/produtos
{
  "produto_cod_barras": "7891234567890",
  "quantidade": 1,
  "observacao": "Bem passado",
  "adicionais": [
    {
      "adicional_id": 10,
      "quantidade": 2
    }
  ]
}
```

**Para Delivery:**

```json
PUT /api/cardapio/client/pedidos/123/itens
{
  "acao": "novo-item",
  "produto_cod_barras": "7891234567890",
  "quantidade": 1,
  "observacao": "Bem passado",
  "adicionais": [
    {
      "adicional_id": 10,
      "quantidade": 2
    }
  ]
}
```

---

## Exemplos Práticos

### Exemplo 1: Pedido de Delivery Simples

```json
POST /api/cardapio/client/pedidos/checkout
{
  "tipo_pedido": "DELIVERY",
  "endereco_id": 10,
  "observacao_geral": "Entregar na portaria",
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "7891234567890",
        "quantidade": 2,
        "adicionais": [
          {
            "adicional_id": 5,
            "quantidade": 1
          }
        ]
      }
    ]
  }
}
```

### Exemplo 2: Pedido de Mesa com Receita e Combo

```json
POST /api/cardapio/client/pedidos/checkout
{
  "empresa_id": 1,
  "tipo_pedido": "MESA",
  "mesa_codigo": "12",
  "num_pessoas": 4,
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "7891111111111",
        "quantidade": 2
      }
    ],
    "receitas": [
      {
        "receita_id": 10,
        "quantidade": 1,
        "adicionais": [
          {
            "adicional_id": 20,
            "quantidade": 2
          }
        ]
      }
    ],
    "combos": [
      {
        "combo_id": 5,
        "quantidade": 1,
        "adicionais": [
          {
            "adicional_id": 30,
            "quantidade": 1
          }
        ]
      }
    ]
  }
}
```

### Exemplo 3: Pedido de Balcão com Múltiplos Itens

```json
POST /api/cardapio/client/pedidos/checkout
{
  "empresa_id": 1,
  "tipo_pedido": "BALCAO",
  "observacao_geral": "Para viagem",
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "7892222222222",
        "quantidade": 3,
        "observacao": "Sem cebola",
        "adicionais": [
          {
            "adicional_id": 10,
            "quantidade": 1
          },
          {
            "adicional_id": 15,
            "quantidade": 2
          }
        ]
      },
      {
        "produto_cod_barras": "7893333333333",
        "quantidade": 1
      }
    ]
  }
}
```

### Exemplo 4: Usando Formato Legado (Compatibilidade)

```json
POST /api/cardapio/client/pedidos/checkout
{
  "empresa_id": 1,
  "tipo_pedido": "MESA",
  "mesa_codigo": "5",
  "itens": [
    {
      "produto_cod_barras": "7891234567890",
      "quantidade": 2,
      "adicionais_ids": [10, 15]  // Formato legado
    }
  ],
  "receitas": [
    {
      "receita_id": 5,
      "quantidade": 1,
      "adicionais_ids": [20]  // Formato legado
    }
  ],
  "combos": [
    {
      "combo_id": 3,
      "quantidade": 2
    }
  ]
}
```

---

## Respostas da API

### PedidoResponse (Delivery)

```typescript
{
  id: number;
  status: "P" | "I" | "R" | "S" | "E" | "C" | "D" | "X" | "A";
  cliente_id?: number;
  empresa_id: number;
  subtotal: number;
  desconto: number;
  taxa_entrega: number;
  taxa_servico: number;
  valor_total: number;
  observacao_geral?: string;
  data_criacao: string;
  data_atualizacao: string;
  itens: Array<{
    id: number;
    produto_cod_barras: string;
    quantidade: number;
    preco_unitario: number;
    observacao?: string;
    produto_descricao_snapshot?: string;
    produto_imagem_snapshot?: string;
  }>;
  produtos: {
    itens: Array<{
      item_id?: number;
      produto_cod_barras?: string;
      descricao?: string;
      imagem?: string;
      quantidade: number;
      preco_unitario: number;
      observacao?: string;
      adicionais: Array<{
        adicional_id?: number;
        nome?: string;
        quantidade: number;
        preco_unitario: number;
        total: number;
      }>;
    }>;
    receitas: Array<{
      item_id?: number;
      receita_id: number;
      nome?: string;
      quantidade: number;
      preco_unitario: number;
      observacao?: string;
      adicionais: Array<{
        adicional_id?: number;
        nome?: string;
        quantidade: number;
        preco_unitario: number;
        total: number;
      }>;
    }>;
    combos: Array<{
      combo_id: number;
      nome?: string;
      quantidade: number;
      preco_unitario: number;
      observacao?: string;
      adicionais: Array<{
        adicional_id?: number;
        nome?: string;
        quantidade: number;
        preco_unitario: number;
        total: number;
      }>;
    }>;
  };
}
```

### PedidoMesaOut

```typescript
{
  id: number;
  empresa_id: number;
  numero_pedido: string;
  mesa_id: number;
  cliente_id?: number;
  num_pessoas?: number;
  status: "P" | "I" | "R" | "E" | "C" | "D" | "X" | "A";
  status_descricao: string;
  observacoes?: string;
  valor_total: number;
  itens: Array<{
    id: number;
    produto_cod_barras: string;
    quantidade: number;
    preco_unitario: number;
    observacao?: string;
    produto_descricao_snapshot?: string;
    produto_imagem_snapshot?: string;
  }>;
  produtos: {
    // Mesma estrutura de ProdutosPedidoOut
  };
  created_at?: string;
  updated_at?: string;
}
```

### PedidoBalcaoOut

```typescript
{
  id: number;
  empresa_id: number;
  numero_pedido: string;
  mesa_id?: number;
  cliente_id?: number;
  status: "P" | "I" | "R" | "E" | "C" | "D" | "X" | "A";
  status_descricao: string;
  observacoes?: string;
  valor_total: number;
  itens: Array<{
    id: number;
    produto_cod_barras: string;
    quantidade: number;
    preco_unitario: number;
    observacao?: string;
    produto_descricao_snapshot?: string;
    produto_imagem_snapshot?: string;
  }>;
  produtos: {
    // Mesma estrutura de ProdutosPedidoOut
  };
  created_at?: string;
  updated_at?: string;
}
```

---

## Regras de Negócio Importantes

### 1. Validações de Produtos

- **Itens normais**: Devem existir na empresa, estar ativos e disponíveis
- **Receitas**: Devem existir, estar ativas, disponíveis e pertencer à empresa
- **Combos**: Devem existir, estar ativos e pertencer à empresa
- **Adicionais**: Devem existir, estar ativos e pertencer à empresa

### 2. Cálculo de Preços

- **Itens normais**: `preco_unitario * quantidade + adicionais`
- **Receitas**: `preco_venda * quantidade + adicionais`
- **Combos**: `preco_total * quantidade + adicionais`
  - Os itens do combo são distribuídos proporcionalmente no pedido
  - O preço é dividido igualmente entre os itens do combo

### 3. Adicionais

- **Para itens normais**: Vinculados ao produto por código de barras
- **Para receitas**: Vinculados diretamente à receita por ID
- **Para combos**: Aplicados ao combo inteiro (não aos itens individuais)
- **Quantidade**: Multiplicada pela quantidade do item principal
  - Exemplo: Item com quantidade 2 + adicional com quantidade 3 = 6 unidades do adicional

### 4. Limites

- Máximo de 200 itens por pedido (soma de itens normais + receitas)
- Quantidade mínima: 1 para todos os produtos
- Quantidade máxima de pessoas na mesa: 50

### 5. Status de Pedidos

- **P**: Pendente
- **I**: Em impressão
- **R**: Em preparo
- **S**: Saiu para entrega (apenas delivery)
- **E**: Entregue
- **C**: Cancelado
- **D**: Editado
- **X**: Em edição
- **A**: Aguardando pagamento

### 6. Compatibilidade

O sistema suporta dois formatos:
- **Novo formato**: `produtos.itens`, `produtos.receitas`, `produtos.combos` com `adicionais` (objetos com quantidade)
- **Formato legado**: `itens`, `receitas`, `combos` na raiz com `adicionais_ids` (lista simples)

**Recomendação**: Use o novo formato para melhor controle de quantidades de adicionais.

---

## Tratamento de Erros

### Erros Comuns

1. **400 Bad Request**
   - Pedido vazio (sem produtos)
   - Produto não encontrado ou indisponível
   - Receita/Combo não encontrado ou inativo
   - Quantidade inválida (< 1)
   - Mesa não encontrada
   - Endereço obrigatório para delivery

2. **403 Forbidden**
   - Pedido não pertence ao cliente
   - Produto não pertence à empresa

3. **404 Not Found**
   - Pedido não encontrado
   - Produto não encontrado
   - Receita/Combo não encontrado
   - Mesa não encontrada

---

## Observações Finais

1. **Snapshots**: O sistema salva snapshots de descrições e imagens dos produtos no momento do pedido para manter histórico.

2. **Adicionais em Combos**: Adicionais de combos são aplicados ao combo inteiro, não aos itens individuais.

3. **Receitas**: Receitas não possuem código de barras próprio, apenas `receita_id`.

4. **Mesa**: Para pedidos de mesa, o `mesa_codigo` é o código numérico da mesa (não o ID).

5. **Balcão**: Pedidos de balcão podem ter mesa associada (opcional).

6. **Preview**: Sempre use o endpoint de preview antes de finalizar para mostrar valores ao cliente.

7. **Endpoint Genérico (NOVO)**: Use os endpoints `/produtos` para adicionar qualquer tipo de produto (produto, receita ou combo). O sistema identifica automaticamente o tipo baseado nos campos preenchidos. Os endpoints `/itens` são mantidos apenas para compatibilidade retroativa.

---

## Exemplo Completo de Integração

```typescript
// 1. Montar carrinho
const carrinho = {
  produtos: {
    itens: [
      {
        produto_cod_barras: "7891234567890",
        quantidade: 2,
        adicionais: [
          { adicional_id: 10, quantidade: 1 }
        ]
      }
    ],
    receitas: [
      {
        receita_id: 5,
        quantidade: 1,
        adicionais: [
          { adicional_id: 20, quantidade: 2 }
        ]
      }
    ],
    combos: [
      {
        combo_id: 3,
        quantidade: 1,
        adicionais: [
          { adicional_id: 25, quantidade: 1 }
        ]
      }
    ]
  }
};

// 2. Preview do checkout
const previewRequest = {
  empresa_id: 1,
  tipo_pedido: "MESA",
  mesa_codigo: "5",
  num_pessoas: 4,
  ...carrinho
};

const preview = await fetch('/api/cardapio/client/pedidos/checkout/preview', {
  method: 'POST',
  body: JSON.stringify(previewRequest)
});

// 3. Finalizar checkout
const checkoutRequest = {
  ...previewRequest,
  meios_pagamento: [
    { id: 1, valor: preview.valor_total }
  ]
};

const pedido = await fetch('/api/cardapio/client/pedidos/checkout', {
  method: 'POST',
  body: JSON.stringify(checkoutRequest)
});
```

---

**Última atualização**: Baseado no código atual do sistema
**Versão da API**: Compatível com endpoints atuais

