# 📘 Documentação: Adicionar Item em Pedido (Admin)

## 🎯 Endpoint

**POST** `/api/pedidos/admin/{pedido_id}/itens`

Adiciona, atualiza ou remove itens de um pedido existente. Funciona para pedidos de **Delivery**, **Mesa** e **Balcão**.

**⚠️ IMPORTANTE - Limitações por Tipo de Pedido:**
- **Delivery**: Aceita **produtos simples**, **receitas** e **combos** (`produto_cod_barras`, `receita_id` ou `combo_id`). ❌ Não aceita complementos.
- **Mesa/Balcão**: Aceita **qualquer tipo** (produto, receita ou combo) com complementos opcionais.

---

## 🔐 Autenticação

**Requerida:** Sim

**Tipo:** Bearer Token (Admin)

**Header:**
```
Authorization: Bearer {token_admin}
```

O token é obtido através do endpoint de login admin.

---

## 📋 Parâmetros de URL

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | `integer` | ✅ Sim | ID do pedido (deve ser > 0) |

**Exemplo:**
```
POST /api/pedidos/admin/21/itens
```

---

## 📦 Body Request

### Schema: `PedidoItemMutationRequest`

```json
{
  "acao": "ADD" | "UPDATE" | "REMOVE",
  "item_id": 0,                    // Opcional - ID do item existente (obrigatório para UPDATE/REMOVE)
  "produto_cod_barras": "string",   // Opcional - Código de barras do produto (obrigatório para ADD item simples)
  "receita_id": 0,                  // Opcional - ID da receita (apenas para mesa/balcão)
  "combo_id": 0,                    // Opcional - ID do combo (apenas para mesa/balcão)
  "quantidade": 1,                   // Opcional - Quantidade (deve ser >= 1)
  "observacao": "string",           // Opcional - Observação livre
  "complementos": [                 // Opcional - Complementos (apenas para mesa/balcão)
    {
      "complemento_id": 0,
      "adicionais": [
        {
          "adicional_id": 0,
          "quantidade": 1
        }
      ]
    }
  ]
}
```

### Campos Detalhados

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `acao` | `enum` | ✅ Sim | Ação a executar: `"ADD"`, `"UPDATE"` ou `"REMOVE"` |
| `item_id` | `integer` | ⚠️ Condicional | ID do item existente. **Obrigatório** para `UPDATE` e `REMOVE` |
| `produto_cod_barras` | `string` | ⚠️ Condicional | Código de barras do produto. **Obrigatório** para `ADD` de item simples |
| `receita_id` | `integer` | ❌ Não | ID da receita (apenas para mesa/balcão) |
| `combo_id` | `integer` | ❌ Não | ID do combo (apenas para mesa/balcão) |
| `quantidade` | `integer` | ⚠️ Condicional | Quantidade do item. **Obrigatório** para `ADD` e `UPDATE`. Deve ser >= 1 |
| `observacao` | `string` | ❌ Não | Observação livre sobre o item |
| `complementos` | `array` | ❌ Não | Lista de complementos com adicionais (apenas para mesa/balcão) |

### Enum: `PedidoItemMutationAction`

```typescript
enum PedidoItemMutationAction {
  ADD = "ADD",      // Adicionar novo item (⚠️ NÃO use "adicionar")
  UPDATE = "UPDATE", // Atualizar item existente
  REMOVE = "REMOVE"  // Remover item existente
}
```

**⚠️ ATENÇÃO:** O valor deve ser exatamente `"ADD"`, `"UPDATE"` ou `"REMOVE"` (em maiúsculas). Não use `"adicionar"`, `"atualizar"` ou `"remover"`.

### Schema: `ItemComplementoRequest`

```json
{
  "complemento_id": 0,
  "adicionais": [
    {
      "adicional_id": 0,
      "quantidade": 1  // >= 1, usado apenas se complemento for quantitativo
    }
  ]
}
```

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

### ❌ ERRADO - Enviando produto_cod_barras com receita
```json
{
  "acao": "ADD",
  "receita_id": 2,
  "produto_cod_barras": "123"  // ❌ ERRADO - não envie cod_barras com receita
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

## 📝 Exemplos de Uso

### 1. Adicionar Produto Simples (Delivery)

```http
POST /api/pedidos/admin/21/itens
Content-Type: application/json
Authorization: Bearer {token}

{
  "acao": "ADD",
  "produto_cod_barras": "7891234567890",
  "quantidade": 2,
  "observacao": "Sem cebola"
}
```

### 2. Adicionar Receita (Delivery ou Mesa/Balcão)

```http
POST /api/pedidos/admin/21/itens
Content-Type: application/json
Authorization: Bearer {token}

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

**⚠️ IMPORTANTE:**
- Para receitas, **NÃO** envie `produto_cod_barras`
- Os `adicionais` devem estar **dentro** de `complementos`, não no nível raiz
- O campo `observacao` deve ser `null` ou string válida (não `"$undefined"` ou `undefined`)

### 3. Adicionar Combo (Delivery ou Mesa/Balcão)

```http
POST /api/pedidos/admin/21/itens
Content-Type: application/json
Authorization: Bearer {token}

{
  "acao": "ADD",
  "combo_id": 8,
  "quantidade": 1,
  "observacao": "Combo completo",
  "complementos": [
    {
      "complemento_id": 1,
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

### 4. Atualizar Item Existente

```http
POST /api/pedidos/admin/21/itens
Content-Type: application/json
Authorization: Bearer {token}

{
  "acao": "UPDATE",
  "item_id": 45,
  "quantidade": 3,
  "observacao": "Atualizado: agora são 3 unidades"
}
```

### 5. Remover Item

```http
POST /api/pedidos/admin/21/itens
Content-Type: application/json
Authorization: Bearer {token}

{
  "acao": "REMOVE",
  "item_id": 45
}
```

---

## ✅ Resposta de Sucesso

**Status Code:** `200 OK`

**Content-Type:** `application/json`

### Schema: `PedidoResponse`

```json
{
  "id": 21,
  "status": "P",
  "cliente_id": 123,
  "telefone_cliente": "11999999999",
  "empresa_id": 1,
  "entregador_id": null,
  "endereco_id": 456,
  "meio_pagamento_id": null,
  "tipo_entrega": "DELIVERY",
  "origem": "APP",
  "subtotal": 51.80,
  "desconto": 0.00,
  "taxa_entrega": 5.00,
  "taxa_servico": 0.00,
  "valor_total": 56.80,
  "previsao_entrega": "2024-01-15T20:30:00Z",
  "distancia_km": 2.5,
  "observacao_geral": null,
  "troco_para": null,
  "cupom_id": null,
  "endereco_snapshot": {
    "logradouro": "Rua Exemplo, 123",
    "bairro": "Centro",
    "cidade": "São Paulo",
    "cep": "01234-567"
  },
  "endereco_geography": null,
  "data_criacao": "2024-01-15T19:00:00Z",
  "data_atualizacao": "2024-01-15T19:15:00Z",
  "itens": [
    {
      "id": 45,
      "produto_cod_barras": "7891234567890",
      "combo_id": null,
      "receita_id": null,
      "quantidade": 2,
      "preco_unitario": 25.90,
      "observacao": "Sem cebola",
      "produto_descricao_snapshot": "Hambúrguer Artesanal",
      "produto_imagem_snapshot": "https://storage.exemplo.com/produtos/uuid.jpg"
    }
  ],
  "transacao": null,
  "pagamento": null,
  "acertado_entregador": null,
  "pago": false,
  "produtos": {
    "itens": [],
    "receitas": [],
    "combos": []
  }
}
```

### Campos da Resposta

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | `integer` | ID do pedido |
| `status` | `enum` | Status do pedido (P=Pendente, A=Aceito, etc.) |
| `cliente_id` | `integer\|null` | ID do cliente |
| `telefone_cliente` | `string\|null` | Telefone do cliente |
| `empresa_id` | `integer` | ID da empresa |
| `entregador_id` | `integer\|null` | ID do entregador (se atribuído) |
| `endereco_id` | `integer\|null` | ID do endereço (delivery) |
| `meio_pagamento_id` | `integer\|null` | ID do meio de pagamento |
| `tipo_entrega` | `enum` | Tipo: `"DELIVERY"`, `"RETIRADA"`, `"BALCAO"`, `"MESA"` |
| `origem` | `enum` | Origem: `"APP"`, `"WEB"`, `"BALCAO"`, etc. |
| `subtotal` | `float` | Subtotal dos itens |
| `desconto` | `float` | Valor do desconto |
| `taxa_entrega` | `float` | Taxa de entrega |
| `taxa_servico` | `float` | Taxa de serviço |
| `valor_total` | `float` | Valor total do pedido |
| `previsao_entrega` | `datetime\|null` | Previsão de entrega |
| `distancia_km` | `float\|null` | Distância em km (delivery) |
| `observacao_geral` | `string\|null` | Observação geral do pedido |
| `troco_para` | `float\|null` | Valor para troco |
| `cupom_id` | `integer\|null` | ID do cupom aplicado |
| `endereco_snapshot` | `object\|null` | Snapshot do endereço no momento do pedido |
| `endereco_geography` | `string\|null` | Coordenadas geográficas |
| `data_criacao` | `datetime` | Data de criação |
| `data_atualizacao` | `datetime` | Data da última atualização |
| `itens` | `array` | Lista de itens do pedido |
| `transacao` | `object\|null` | Dados da transação de pagamento |
| `pagamento` | `object\|null` | Resumo do pagamento |
| `acertado_entregador` | `boolean\|null` | Se foi acertado com entregador |
| `pago` | `boolean` | Se o pedido foi pago |
| `produtos` | `object` | Agrupamento de produtos, receitas e combos |

### Schema: `ItemPedidoResponse`

```json
{
  "id": 45,
  "produto_cod_barras": "7891234567890",
  "combo_id": null,
  "receita_id": null,
  "quantidade": 2,
  "preco_unitario": 25.90,
  "observacao": "Sem cebola",
  "produto_descricao_snapshot": "Hambúrguer Artesanal",
  "produto_imagem_snapshot": "https://storage.exemplo.com/produtos/uuid.jpg"
}
```

---

## ❌ Respostas de Erro

### 400 Bad Request - Validação

```json
{
  "detail": "produto_cod_barras é obrigatório para adicionar item simples"
}
```

**Possíveis erros:**
- `"produto_cod_barras é obrigatório para adicionar item simples"`
- `"item_id é obrigatório para remover item"`
- `"Quantidade deve ser maior que zero"`
- `"Atualização parcial de itens não suportada para mesa"`

### 404 Not Found - Pedido não encontrado

```json
{
  "detail": "Pedido não encontrado"
}
```

### 404 Not Found - Produto não encontrado

```json
{
  "detail": "Produto 7891234567890 não encontrado"
}
```

### 400 Bad Request - Produto indisponível

```json
{
  "detail": "Produto indisponível: 7891234567890"
}
```

### 400 Bad Request - Complementos não suportados em Delivery

```json
{
  "detail": "Complementos não são suportados para pedidos de delivery."
}
```

**Nota:** Receitas e combos são suportados em delivery, apenas complementos não são permitidos.

### 400 Bad Request - Pedido fechado/cancelado

```json
{
  "detail": "Pedido fechado/cancelado"
}
```

**Nota:** Não é possível adicionar itens em pedidos com status `"C"` (Cancelado) ou `"E"` (Entregue/Fechado).

---

## 🔍 Validações e Regras de Negócio

### Para Adicionar Item (`acao: "ADD"`)

1. **Delivery (Produto, Receita ou Combo):**
   - ✅ `acao` deve ser `"ADD"` (não `"adicionar"`)
   - ✅ Deve informar **exatamente um** dos seguintes: `produto_cod_barras`, `receita_id` ou `combo_id`
   - ✅ `quantidade` deve ser >= 1
   - ✅ Produto/Receita/Combo deve existir e estar disponível
   - ✅ Pedido não pode estar fechado/cancelado
   - ❌ **NÃO** envie `complementos` para delivery (não suportado)

2. **Receita (Mesa/Balcão):**
   - ✅ `acao` deve ser `"ADD"` (não `"adicionar"`)
   - ✅ `receita_id` é **obrigatório**
   - ✅ `quantidade` deve ser >= 1
   - ✅ Receita deve existir
   - ✅ Pedido não pode estar fechado/cancelado
   - ❌ **NÃO** envie `produto_cod_barras` quando for receita
   - ✅ `complementos` são opcionais
   - ⚠️ `adicionais` devem estar **dentro** de `complementos`, não no nível raiz

3. **Combo (Mesa/Balcão):**
   - ✅ `acao` deve ser `"ADD"` (não `"adicionar"`)
   - ✅ `combo_id` é **obrigatório**
   - ✅ `quantidade` deve ser >= 1
   - ✅ Combo deve existir
   - ✅ Pedido não pode estar fechado/cancelado
   - ❌ **NÃO** envie `produto_cod_barras` quando for combo
   - ✅ `complementos` são opcionais
   - ⚠️ `adicionais` devem estar **dentro** de `complementos`, não no nível raiz

### Para Atualizar Item (`acao: "UPDATE"`)

1. **Delivery:**
   - ✅ `item_id` é **obrigatório**
   - ✅ `quantidade` pode ser atualizada
   - ✅ `observacao` pode ser atualizada
   - ✅ Item deve existir no pedido

2. **Mesa/Balcão:**
   - ⚠️ Atualização parcial **não suportada** para mesa/balcão
   - Use `REMOVE` + `ADD` para alterar itens

### Para Remover Item (`acao: "REMOVE"`)

1. ✅ `item_id` é **obrigatório**
2. ✅ Item deve existir no pedido
3. ✅ Pedido não pode estar fechado/cancelado

---

## 📌 Observações Importantes

1. **Tipo de Pedido:**
   - O endpoint detecta automaticamente o tipo de pedido (Delivery, Mesa, Balcão)
   - Comportamento e validações variam conforme o tipo

2. **Limitações por Tipo:**
   - **Delivery**: 
     - ✅ Aceita produtos simples (`produto_cod_barras`)
     - ✅ Aceita receitas (`receita_id`)
     - ✅ Aceita combos (`combo_id`)
     - ❌ **NÃO aceita** complementos
     - Se tentar enviar complementos, retornará erro 400
   
   - **Mesa/Balcão**:
     - ✅ Aceita produtos simples (`produto_cod_barras`)
     - ✅ Aceita receitas (`receita_id`)
     - ✅ Aceita combos (`combo_id`)
     - ✅ Aceita complementos (opcional)

3. **Complementos:**
   - Apenas disponíveis para pedidos de **Mesa** e **Balcão**
   - Não aplicável para **Delivery** (causará erro se enviado)

4. **Receitas e Combos:**
   - ✅ Disponíveis para pedidos de **Delivery**, **Mesa** e **Balcão**
   - Funcionam da mesma forma em todos os tipos de pedido

4. **Preço:**
   - O preço unitário é obtido automaticamente do produto/receita/combo
   - Não é necessário enviar o preço no request

5. **Snapshot:**
   - Descrição e imagem do produto são salvos como snapshot no momento da adição
   - Garante histórico mesmo se o produto for alterado depois

---

## 🔗 Endpoints Relacionados

- **Atualizar item específico:** `PATCH /api/pedidos/admin/{pedido_id}/itens/{item_id}`
- **Remover item específico:** `DELETE /api/pedidos/admin/{pedido_id}/itens/{item_id}`
- **Obter pedido:** `GET /api/pedidos/admin/{pedido_id}`
- **Listar pedidos:** `GET /api/pedidos/admin`

---

## 💡 Exemplo de Implementação (JavaScript/TypeScript)

```typescript
interface PedidoItemMutationRequest {
  acao: "ADD" | "UPDATE" | "REMOVE";
  item_id?: number;
  produto_cod_barras?: string;
  receita_id?: number;
  combo_id?: number;
  quantidade?: number;
  observacao?: string;
  complementos?: Array<{
    complemento_id: number;
    adicionais: Array<{
      adicional_id: number;
      quantidade: number;
    }>;
  }>;
}

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

// Exemplo de uso
const novoItem = {
  acao: "ADD",
  produto_cod_barras: "7891234567890",
  quantidade: 2,
  observacao: "Sem cebola"
};

try {
  const pedidoAtualizado = await adicionarItemPedido(21, novoItem, token);
  console.log("Item adicionado:", pedidoAtualizado);
} catch (error) {
  console.error("Erro:", error.message);
}
```

---

## 📚 Referências

- Schema completo: `app/api/pedidos/schemas/schema_pedido_admin.py`
- Implementação: `app/api/pedidos/router/admin/router_pedidos_admin.py`
- Service: `app/api/pedidos/services/service_pedido_admin.py`

