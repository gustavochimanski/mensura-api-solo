# 📚 Documentação de Migração: Adicionais → Complementos (Client)

## 📋 Índice
1. [Visão Geral](#visão-geral)
2. [O que mudou?](#o-que-mudou)
3. [Endpoints Obsoletos](#endpoints-obsoletos)
4. [Novos Endpoints](#novos-endpoints)
5. [Estrutura de Dados](#estrutura-de-dados)
6. [Exemplos Práticos](#exemplos-práticos)
7. [FAQ](#faq)

---

## 🎯 Visão Geral

A API foi atualizada para usar **Complementos** ao invés de **Adicionais diretos**. Agora os adicionais estão organizados dentro de grupos chamados "Complementos", que têm configurações próprias.

### Por que mudou?

A nova estrutura permite:
- ✅ Agrupar adicionais relacionados (ex: "Molhos", "Extras", "Tamanhos")
- ✅ Configurar regras por grupo (obrigatório, quantitativo, múltipla escolha)
- ✅ Melhor organização e experiência do usuário

---

## 🔄 O que mudou?

### Antes (Estrutura Antiga) ❌

```json
{
  "produto_cod_barras": "7891234567890",
  "quantidade": 1,
  "adicionais": [
    { "adicional_id": 1, "quantidade": 1 },
    { "adicional_id": 2, "quantidade": 1 }
  ]
}
```

### Agora (Nova Estrutura) ✅

```json
{
  "produto_cod_barras": "7891234567890",
  "quantidade": 1,
  "complementos": [
    {
      "complemento_id": 10,
      "adicionais": [
        { "adicional_id": 1, "quantidade": 1 },
        { "adicional_id": 2, "quantidade": 1 }
      ]
    }
  ]
}
```

---

## 🚫 Endpoints Obsoletos

### ⚠️ NÃO USE MAIS ESTES ENDPOINTS

| Método | Endpoint | Status | Substituição |
|--------|----------|--------|--------------|
| `GET` | `/api/catalogo/client/adicionais/produto/{cod_barras}` | ❌ **OBSOLETO** | Use `/api/catalogo/client/complementos/produto/{cod_barras}` |
| `GET` | `/api/catalogo/client/adicionais/combo/{combo_id}` | ❌ **OBSOLETO** | Use `/api/catalogo/client/complementos/combo/{combo_id}` |
| `GET` | `/api/catalogo/client/adicionais/receita/{receita_id}` | ❌ **OBSOLETO** | Use `/api/catalogo/client/complementos/receita/{receita_id}` |

### ⚠️ Campos Removidos dos Schemas

**NÃO USE MAIS:**
- `adicionais` (array de adicionais diretos)
- `adicionais_ids` (array de IDs de adicionais)

**USE AGORA:**
- `complementos` (array de complementos com seus adicionais)

---

## ✅ Novos Endpoints

### 1. Listar Complementos de um Produto

**Endpoint:** `GET /api/catalogo/client/complementos/produto/{cod_barras}`

**Headers:**
```
X-Super-Token: {seu_token}
```

**Query Parameters:**
- `apenas_ativos` (boolean, default: `true`) - Filtrar apenas complementos ativos

**Response:**
```json
[
  {
    "id": 10,
    "nome": "Molhos",
    "descricao": "Escolha seus molhos favoritos",
    "obrigatorio": false,
    "quantitativo": false,
    "permite_multipla_escolha": true,
    "ordem": 1,
    "adicionais": [
      {
        "id": 1,
        "nome": "Ketchup",
        "preco": 0.00,
        "ordem": 1
      },
      {
        "id": 2,
        "nome": "Mostarda",
        "preco": 0.00,
        "ordem": 2
      },
      {
        "id": 3,
        "nome": "Barbecue",
        "preco": 2.00,
        "ordem": 3
      }
    ]
  },
  {
    "id": 11,
    "nome": "Extras",
    "descricao": "Adicione extras ao seu pedido",
    "obrigatorio": false,
    "quantitativo": true,
    "permite_multipla_escolha": true,
    "ordem": 2,
    "adicionais": [
      {
        "id": 4,
        "nome": "Bacon",
        "preco": 5.00,
        "ordem": 1
      },
      {
        "id": 5,
        "nome": "Queijo Extra",
        "preco": 3.00,
        "ordem": 2
      }
    ]
  }
]
```

### 2. Listar Complementos de um Combo

**Endpoint:** `GET /api/catalogo/client/complementos/combo/{combo_id}`

**Headers:**
```
X-Super-Token: {seu_token}
```

**Query Parameters:**
- `apenas_ativos` (boolean, default: `true`)

**Response:** Mesma estrutura do endpoint de produto

### 3. Listar Complementos de uma Receita

**Endpoint:** `GET /api/catalogo/client/complementos/receita/{receita_id}`

**Headers:**
```
X-Super-Token: {seu_token}
```

**Query Parameters:**
- `apenas_ativos` (boolean, default: `true`)

**Response:** Mesma estrutura do endpoint de produto

---

## 📊 Estrutura de Dados

### Complemento

Um **Complemento** é um grupo de adicionais com configurações próprias:

```typescript
interface Complemento {
  id: number;
  nome: string;                    // Ex: "Molhos", "Extras", "Tamanhos"
  descricao?: string;
  obrigatorio: boolean;             // Se o complemento é obrigatório
  quantitativo: boolean;            // Se permite quantidade (ex: 2x bacon)
  permite_multipla_escolha: boolean; // Se pode escolher múltiplos adicionais
  ordem: number;                    // Ordem de exibição
  adicionais: Adicional[];          // Lista de adicionais dentro do complemento
}
```

### Adicional (dentro de Complemento)

Um **Adicional** agora está sempre dentro de um complemento:

```typescript
interface Adicional {
  id: number;
  nome: string;                     // Ex: "Ketchup", "Bacon"
  preco: number;                    // Preço do adicional
  ordem: number;                    // Ordem dentro do complemento
}
```

### Configurações do Complemento

#### `obrigatorio: true`
- O cliente **DEVE** selecionar pelo menos um adicional deste complemento
- Se não selecionar, o pedido será rejeitado

#### `quantitativo: true`
- Permite escolher quantidade do adicional (ex: 2x bacon, 3x queijo)
- O campo `quantidade` no `ItemAdicionalComplementoRequest` é respeitado

#### `quantitativo: false`
- Quantidade sempre será 1
- O campo `quantidade` enviado será ignorado

#### `permite_multipla_escolha: true`
- Permite selecionar múltiplos adicionais no mesmo complemento
- Ex: Ketchup + Mostarda + Barbecue

#### `permite_multipla_escolha: false`
- Apenas um adicional pode ser selecionado
- Se enviar múltiplos, apenas o primeiro será considerado

---

## 💡 Exemplos Práticos

### Exemplo 1: Produto com Complementos

#### 1. Buscar complementos do produto

```http
GET /api/catalogo/client/complementos/produto/7891234567890
X-Super-Token: abc123
```

#### 2. Criar pedido com complementos

```http
POST /api/pedidos/client/checkout
X-Super-Token: abc123
Content-Type: application/json

{
  "empresa_id": 1,
  "tipo_pedido": "DELIVERY",
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "7891234567890",
        "quantidade": 2,
        "complementos": [
          {
            "complemento_id": 10,
            "adicionais": [
              { "adicional_id": 1, "quantidade": 1 },  // Ketchup
              { "adicional_id": 3, "quantidade": 1 }   // Barbecue
            ]
          },
          {
            "complemento_id": 11,
            "adicionais": [
              { "adicional_id": 4, "quantidade": 2 }   // 2x Bacon
            ]
          }
        ]
      }
    ]
  }
}
```

### Exemplo 2: Receita com Complementos

```http
POST /api/pedidos/client/checkout
X-Super-Token: abc123
Content-Type: application/json

{
  "empresa_id": 1,
  "tipo_pedido": "DELIVERY",
  "produtos": {
    "receitas": [
      {
        "receita_id": 5,
        "quantidade": 1,
        "complementos": [
          {
            "complemento_id": 10,
            "adicionais": [
              { "adicional_id": 1, "quantidade": 1 }
            ]
          }
        ]
      }
    ]
  }
}
```

### Exemplo 3: Combo com Complementos

```http
POST /api/pedidos/client/checkout
X-Super-Token: abc123
Content-Type: application/json

{
  "empresa_id": 1,
  "tipo_pedido": "DELIVERY",
  "produtos": {
    "combos": [
      {
        "combo_id": 3,
        "quantidade": 1,
        "complementos": [
          {
            "complemento_id": 10,
            "adicionais": [
              { "adicional_id": 1, "quantidade": 1 },
              { "adicional_id": 2, "quantidade": 1 }
            ]
          }
        ]
      }
    ]
  }
}
```

### Exemplo 4: Produto sem Complementos

```http
POST /api/pedidos/client/checkout
X-Super-Token: abc123
Content-Type: application/json

{
  "empresa_id": 1,
  "tipo_pedido": "DELIVERY",
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "7891234567890",
        "quantidade": 1
        // complementos é opcional - pode ser null ou omitido
      }
    ]
  }
}
```

---

## 📝 Schemas Atualizados

### ItemPedidoRequest

```typescript
interface ItemPedidoRequest {
  produto_cod_barras: string;
  quantidade: number;
  observacao?: string;
  
  // NOVO: apenas complementos
  complementos?: ItemComplementoRequest[];
  
  // REMOVIDO: adicionais (não use mais)
  // REMOVIDO: adicionais_ids (não use mais)
}
```

### ItemComplementoRequest

```typescript
interface ItemComplementoRequest {
  complemento_id: number;
  adicionais: ItemAdicionalComplementoRequest[];
}
```

### ItemAdicionalComplementoRequest

```typescript
interface ItemAdicionalComplementoRequest {
  adicional_id: number;
  quantidade: number;  // Usado apenas se complemento.quantitativo = true
}
```

### ReceitaPedidoRequest

```typescript
interface ReceitaPedidoRequest {
  receita_id: number;
  quantidade: number;
  observacao?: string;
  
  // NOVO: apenas complementos
  complementos?: ItemComplementoRequest[];
  
  // REMOVIDO: adicionais (não use mais)
  // REMOVIDO: adicionais_ids (não use mais)
}
```

### ComboPedidoRequest

```typescript
interface ComboPedidoRequest {
  combo_id: number;
  quantidade: number;
  
  // NOVO: apenas complementos
  complementos?: ItemComplementoRequest[];
  
  // REMOVIDO: adicionais (não use mais)
}
```

---

## 🔍 Validações e Regras

### 1. Complemento Obrigatório

Se `complemento.obrigatorio = true`:
- ✅ Pelo menos um adicional deve ser selecionado
- ❌ Se não selecionar, o pedido será rejeitado com erro 400

**Exemplo de erro:**
```json
{
  "detail": "Complemento 'Molhos' é obrigatório e requer pelo menos um adicional selecionado"
}
```

### 2. Quantidade

Se `complemento.quantitativo = true`:
- ✅ A quantidade enviada será respeitada
- ✅ Pode enviar `quantidade: 2` para "2x Bacon"

Se `complemento.quantitativo = false`:
- ⚠️ A quantidade sempre será 1
- ⚠️ O valor enviado em `quantidade` será ignorado

### 3. Múltipla Escolha

Se `complemento.permite_multipla_escolha = true`:
- ✅ Pode selecionar múltiplos adicionais
- ✅ Ex: `[{adicional_id: 1}, {adicional_id: 2}, {adicional_id: 3}]`

Se `complemento.permite_multipla_escolha = false`:
- ⚠️ Apenas o primeiro adicional será considerado
- ⚠️ Outros serão ignorados

### 4. Adicionais Inválidos

- ❌ Não pode enviar `adicional_id` que não existe no complemento
- ❌ Não pode enviar `complemento_id` que não está vinculado ao produto/receita/combo

**Exemplo de erro:**
```json
{
  "detail": "Adicional ID 999 não pertence ao complemento ID 10"
}
```

---

## ❓ FAQ

### 1. O que acontece se eu não enviar `complementos`?

✅ **Resposta:** Nada! O campo `complementos` é opcional. Se o produto não tiver complementos ou você não quiser selecionar nenhum, simplesmente omita o campo ou envie `null`.

### 2. Posso enviar um complemento vazio (sem adicionais)?

✅ **Resposta:** Sim, mas apenas se `complemento.obrigatorio = false`. Se for obrigatório, pelo menos um adicional deve ser selecionado.

### 3. Como saber quais complementos um produto tem?

✅ **Resposta:** Use o endpoint `GET /api/catalogo/client/complementos/produto/{cod_barras}` antes de criar o pedido.

### 4. O que acontece se eu enviar `quantidade: 5` em um complemento não quantitativo?

⚠️ **Resposta:** A quantidade será ignorada e sempre será 1. Não há erro, mas o valor será ajustado automaticamente.

### 5. Posso selecionar o mesmo adicional múltiplas vezes?

✅ **Resposta:** Sim, se `complemento.permite_multipla_escolha = true`. Você pode enviar:
```json
{
  "complemento_id": 10,
  "adicionais": [
    { "adicional_id": 1, "quantidade": 1 },
    { "adicional_id": 1, "quantidade": 1 }  // Mesmo adicional duas vezes
  ]
}
```

### 6. Os endpoints antigos ainda funcionam?

❌ **Resposta:** Não! Os endpoints antigos de adicionais foram descontinuados. Você DEVE usar os novos endpoints de complementos.

### 7. Como migrar meu código existente?

✅ **Resposta:** 
1. Substitua chamadas a `/api/catalogo/client/adicionais/*` por `/api/catalogo/client/complementos/*`
2. Atualize os schemas para usar `complementos` ao invés de `adicionais`
3. Ajuste a UI para mostrar complementos agrupados
4. Teste o fluxo completo de pedidos

### 8. Como calcular o preço total com complementos?

✅ **Resposta:** O backend calcula automaticamente. Apenas envie os complementos selecionados e o `valor_total` do pedido já virá calculado na resposta.

---

## 🔄 Guia de Migração Rápida

### Passo 1: Atualizar busca de adicionais

**Antes:**
```javascript
GET /api/catalogo/client/adicionais/produto/7891234567890
```

**Agora:**
```javascript
GET /api/catalogo/client/complementos/produto/7891234567890
```

### Passo 2: Atualizar estrutura do pedido

**Antes:**
```javascript
{
  produto_cod_barras: "7891234567890",
  quantidade: 1,
  adicionais: [
    { adicional_id: 1, quantidade: 1 }
  ]
}
```

**Agora:**
```javascript
{
  produto_cod_barras: "7891234567890",
  quantidade: 1,
  complementos: [
    {
      complemento_id: 10,
      adicionais: [
        { adicional_id: 1, quantidade: 1 }
      ]
    }
  ]
}
```

### Passo 3: Atualizar UI

- Mostrar complementos agrupados
- Respeitar `obrigatorio`, `quantitativo`, `permite_multipla_escolha`
- Validar seleções antes de enviar

---

## 📌 Checklist de Migração

- [ ] Substituir endpoints de adicionais por complementos
- [ ] Atualizar schemas de request/response
- [ ] Atualizar UI para mostrar complementos agrupados
- [ ] Implementar validações de complementos obrigatórios
- [ ] Testar fluxo completo de pedidos
- [ ] Validar cálculos de preços
- [ ] Atualizar documentação interna
- [ ] Treinar equipe sobre nova estrutura

---

## 🆘 Suporte

Em caso de dúvidas ou problemas:
1. Consulte esta documentação
2. Verifique os exemplos práticos
3. Entre em contato com o suporte técnico

---

**Última atualização:** 2024
**Versão:** 1.0.0

