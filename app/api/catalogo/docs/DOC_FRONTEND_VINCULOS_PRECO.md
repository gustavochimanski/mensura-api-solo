# Documentação Frontend: Vínculos e Preço de Adicionais em Complementos

## 🎯 Resumo para Frontend

Esta documentação explica como funciona o sistema de vínculos de itens (produto/receita/combo) em complementos e como o **preço do adicional** é definido e utilizado.

**⚠️ IMPORTANTE: Mudança Arquitetural**
- **Antes:** Existia CRUD de adicionais (`/api/catalogo/admin/adicionais`)
- **Agora:** Adicionais são vínculos de produtos/receitas/combos em complementos
- **Endpoints de adicionais foram REMOVIDOS** (veja seção 0 abaixo)

---

## 0. ⚠️ Endpoints Removidos - CRUD de Adicionais

### 0.1 Endpoints que NÃO funcionam mais

Os seguintes endpoints foram **removidos** e retornam **404 Not Found**:

```
❌ GET    /api/catalogo/admin/adicionais?empresa_id={id}
❌ GET    /api/catalogo/admin/adicionais?empresa_id={id}&search={termo}
❌ POST   /api/catalogo/admin/adicionais
❌ GET    /api/catalogo/admin/adicionais/{id}
❌ PUT    /api/catalogo/admin/adicionais/{id}
❌ DELETE /api/catalogo/admin/adicionais/{id}
❌ PUT    /api/catalogo/admin/adicionais/{id}/imagem
```

### 0.2 Por que foram removidos?

**Antes:**
- Existia uma entidade separada `adicionais` no banco
- Era necessário cadastrar adicionais separadamente
- Depois vinculava adicionais a complementos

**Agora:**
- Não existe mais a entidade `adicionais`
- Adicionais são **vínculos** de produtos/receitas/combos em complementos
- Você vincula diretamente produtos/receitas/combos aos complementos
- O vínculo define o preço do adicional quando necessário

### 0.3 Como fazer agora?

**Antes (não funciona mais):**
```typescript
// ❌ NÃO FUNCIONA MAIS
// 1. Criar adicional
await criarAdicional({
  empresa_id: 1,
  nome: "Bacon",
  preco: 5.00
});

// 2. Vincular adicional ao complemento
await vincularItensComplemento(complementoId, {
  item_ids: [adicionalId]
});
```

**Agora (novo fluxo):**
```typescript
// ✅ NOVO FLUXO
// Vincular produto diretamente ao complemento
await vincularItensComplemento(complementoId, {
  items: [{
    tipo: "produto",
    produto_cod_barras: "BACON001",
    ordem: 0,
    preco_complemento: 5.00  // Preço específico neste complemento
  }]
});
```

### 0.4 Migração do Frontend

**O que mudar:**
1. **Remover chamadas** aos endpoints `/api/catalogo/admin/adicionais/*`
2. **Usar endpoints de complementos** para vincular itens:
   - `POST /api/catalogo/admin/complementos/{id}/itens/vincular`
   - `POST /api/catalogo/admin/complementos/{id}/itens/adicionar`
3. **Usar produtos/receitas/combos** diretamente como adicionais
4. **Definir preço** via `preco_complemento` no vínculo quando necessário

**O que permanece igual:**
- Respostas de complementos continuam retornando `adicionais` (lista)
- Estrutura de `AdicionalResponse` permanece igual
- Uso em pedidos/carrinho permanece igual (usa `adicional_id`)

**Diferença importante:**
- `adicional_id` agora é o **ID do vínculo** (`complemento_vinculo_item.id`), não mais o ID de um cadastro de adicional

---

## 1. Conceitos Importantes

### 1.1 O que é um Vínculo?

Um **vínculo** (`complemento_vinculo_item`) é a relação entre:
- Um **complemento** (ex: "Acompanhamentos")
- Um **item** que pode ser: produto, receita ou combo (ex: "Bacon", "Molho Especial", "Combo 1")

### 1.2 Preço do Adicional

O preço de um adicional em um complemento pode ser:
- **Preço específico no complemento**: Definido no vínculo (`preco_complemento`)
- **Preço padrão**: Preço da entidade (produto/receita/combo)

**Prioridade:** Preço específico > Preço padrão

---

## 2. Endpoints Disponíveis

### 2.1 Vincular Múltiplos Itens a um Complemento

**Endpoint:** `POST /api/catalogo/admin/complementos/{complemento_id}/itens/vincular`

**Request Body:**
```json
{
  "items": [
    {
      "tipo": "produto",
      "produto_cod_barras": "123456",
      "ordem": 0,
      "preco_complemento": 5.50
    },
    {
      "tipo": "receita",
      "receita_id": 2,
      "ordem": 1
      // preco_complemento não informado = usa preço padrão da receita
    },
    {
      "tipo": "combo",
      "combo_id": 3,
      "ordem": 2,
      "preco_complemento": 10.00
    }
  ],
  "ordens": [0, 1, 2],  // Opcional: sobrescreve ordem dos items
  "precos": [5.50, null, 10.00]  // Opcional: sobrescreve preco_complemento dos items
}
```

**Campos do `ItemVinculoInput`:**
- `tipo` (obrigatório): `"produto"` | `"receita"` | `"combo"`
- `produto_cod_barras` (obrigatório se tipo=produto): Código de barras do produto
- `receita_id` (obrigatório se tipo=receita): ID da receita
- `combo_id` (obrigatório se tipo=combo): ID do combo
- `ordem` (opcional): Ordem de exibição no complemento
- `preco_complemento` (opcional): Preço específico deste adicional neste complemento

**Campos opcionais do request:**
- `ordens` (opcional): Lista de ordens que sobrescreve `ordem` dos items (por índice)
- `precos` (opcional): Lista de preços que sobrescreve `preco_complemento` dos items (por índice)

**Prioridade de Preço:**
1. `item.preco_complemento` (maior prioridade)
2. `request.precos[i]` (se `item.preco_complemento` não informado)
3. Preço padrão da entidade (se nenhum preço específico informado)

**Response:**
```json
{
  "complemento_id": 1,
  "adicionais": [
    {
      "id": 10,  // ID do VÍNCULO (não do produto/receita/combo)
      "nome": "Bacon",
      "descricao": "Bacon crocante",
      "imagem": "https://...",
      "preco": 5.50,  // Preço efetivo (preco_complemento ou padrão)
      "custo": 2.00,
      "ativo": true,
      "ordem": 0,
      "created_at": "2026-01-22T10:00:00",
      "updated_at": "2026-01-22T10:00:00"
    },
    {
      "id": 11,  // ID do VÍNCULO
      "nome": "Molho Especial",
      "preco": 3.00,  // Preço padrão da receita (preco_complemento não informado)
      "ordem": 1,
      ...
    }
  ],
  "message": "Itens vinculados com sucesso"
}
```

**⚠️ IMPORTANTE:**
- O campo `id` em cada `adicional` é o **ID do vínculo** (`complemento_vinculo_item.id`)
- Use este `id` para:
  - Atualizar preço: `PUT /{complemento_id}/itens/{id}/preco`
  - Desvincular: `DELETE /{complemento_id}/itens/{id}`
  - Atualizar ordem: `PUT /{complemento_id}/itens/ordem` (com `item_id` = `id` do vínculo)
  - Enviar em pedidos: `adicional_id` = `id` do vínculo

---

### 2.2 Adicionar um Único Item a um Complemento

**Endpoint:** `POST /api/catalogo/admin/complementos/{complemento_id}/itens/adicionar`

**Request Body:**
```json
{
  "tipo": "produto",
  "produto_cod_barras": "123456",
  "ordem": 0,
  "preco_complemento": 5.50
}
```

**Response:**
```json
{
  "complemento_id": 1,
  "item_vinculado": {
    "id": 12,  // ID do VÍNCULO
    "nome": "Bacon",
    "preco": 5.50,
    ...
  },
  "message": "Item vinculado com sucesso"
}
```

---

### 2.3 Listar Itens de um Complemento

**Endpoint:** `GET /api/catalogo/admin/complementos/{complemento_id}/itens`

**Response:**
```json
{
  "complemento_id": 1,
  "adicionais": [
    {
      "id": 10,  // ID do VÍNCULO
      "nome": "Bacon",
      "preco": 5.50,  // Preço efetivo
      "ordem": 0,
      ...
    },
    ...
  ]
}
```

**⚠️ IMPORTANTE:**
- O campo `id` é o **ID do vínculo**, não do produto/receita/combo
- O campo `preco` é o **preço efetivo** (preço específico ou padrão)

---

### 2.4 Atualizar Preço de um Item

**Endpoint:** `PUT /api/catalogo/admin/complementos/{complemento_id}/itens/{item_id}/preco`

**⚠️ IMPORTANTE:** `item_id` = ID do **vínculo** (o `id` retornado em `adicionais`)

**Request Body:**
```json
{
  "preco": 7.00
}
```

**Response:**
```json
{
  "id": 10,  // ID do vínculo
  "nome": "Bacon",
  "preco": 7.00,  // Preço atualizado
  ...
}
```

**Comportamento:**
- Atualiza o `preco_complemento` do vínculo
- O preço passa a ser fixo neste complemento (não usa mais o preço padrão)

---

### 2.5 Remover Preço Específico (Usar Preço Padrão)

Para remover o preço específico e voltar a usar o preço padrão da entidade:

**Endpoint:** `PUT /api/catalogo/admin/complementos/{complemento_id}/itens/{item_id}/preco`

**Request Body:**
```json
{
  "preco": null
}
```

**Ou enviar `0` e tratar no backend como remoção do preço específico.**

**Nota:** Verifique se o backend aceita `null` ou `0` para remover o preço específico. Se não aceitar, será necessário desvincular e vincular novamente sem `preco_complemento`.

---

### 2.6 Desvincular um Item

**Endpoint:** `DELETE /api/catalogo/admin/complementos/{complemento_id}/itens/{item_id}`

**⚠️ IMPORTANTE:** `item_id` = ID do **vínculo** (o `id` retornado em `adicionais`)

**Response:**
```json
{
  "message": "Item desvinculado com sucesso"
}
```

---

### 2.7 Atualizar Ordem dos Itens

**Endpoint:** `PUT /api/catalogo/admin/complementos/{complemento_id}/itens/ordem`

**Request Body (Formato Completo):**
```json
{
  "item_ordens": [
    {
      "item_id": 10,  // ID do VÍNCULO
      "ordem": 2
    },
    {
      "item_id": 11,  // ID do VÍNCULO
      "ordem": 0
    },
    {
      "item_id": 12,  // ID do VÍNCULO
      "ordem": 1
    }
  ]
}
```

**Request Body (Formato Simples):**
```json
{
  "item_ids": [11, 12, 10]  // IDs dos vínculos na ordem desejada (ordem = índice)
}
```

**⚠️ IMPORTANTE:** `item_id` em `item_ordens` ou IDs em `item_ids` = IDs dos **vínculos**

---

## 3. Fluxo de Uso no Frontend

### 3.1 Criar/Editar Complemento com Itens

```typescript
// 1. Criar ou buscar complemento
const complemento = await criarComplemento({
  empresa_id: 1,
  nome: "Acompanhamentos",
  descricao: "Escolha seus acompanhamentos"
});

// 2. Vincular itens ao complemento
const response = await vincularItensComplemento(complemento.id, {
  items: [
    {
      tipo: "produto",
      produto_cod_barras: "BACON001",
      ordem: 0,
      preco_complemento: 5.50  // Preço específico
    },
    {
      tipo: "receita",
      receita_id: 2,
      ordem: 1
      // Sem preco_complemento = usa preço padrão da receita
    }
  ]
});

// 3. Os itens retornados têm ID do vínculo
response.adicionais.forEach(adicional => {
  console.log(`Vínculo ID: ${adicional.id}, Preço: ${adicional.preco}`);
});
```

### 3.2 Atualizar Preço de um Adicional

```typescript
// item_id = ID do vínculo (retornado em adicionais)
const vinculoId = 10;  // ID do vínculo, não do produto

await atualizarPrecoItemComplemento(complementoId, vinculoId, {
  preco: 7.00
});
```

### 3.3 Usar em Pedidos/Carrinho

```typescript
// Ao adicionar item ao carrinho com complementos
const pedidoItem = {
  produto_cod_barras: "HAMBURGUER001",
  quantidade: 1,
  complementos: [
    {
      complemento_id: 1,
      adicionais: [
        {
          adicional_id: 10,  // ID do VÍNCULO (não do produto)
          quantidade: 1
        }
      ]
    }
  ]
};
```

**⚠️ IMPORTANTE:** `adicional_id` no pedido/carrinho = ID do **vínculo** (`complemento_vinculo_item.id`)

---

## 4. Exemplos Práticos

### 4.1 Cenário: Produto com Preço Diferente em Complementos Diferentes

**Situação:**
- Produto "Bacon" tem preço padrão: R$ 3,00
- No complemento "Acompanhamentos": deve custar R$ 5,00
- No complemento "Extras": deve custar R$ 4,00

**Solução:**
```typescript
// Vincular no complemento "Acompanhamentos"
await vincularItensComplemento(acompanhamentosId, {
  items: [{
    tipo: "produto",
    produto_cod_barras: "BACON001",
    ordem: 0,
    preco_complemento: 5.00  // Preço específico
  }]
});

// Vincular no complemento "Extras"
await vincularItensComplemento(extrasId, {
  items: [{
    tipo: "produto",
    produto_cod_barras: "BACON001",
    ordem: 0,
    preco_complemento: 4.00  // Preço específico diferente
  }]
});
```

**Resultado:**
- No complemento "Acompanhamentos": Bacon aparece com preço R$ 5,00
- No complemento "Extras": Bacon aparece com preço R$ 4,00
- Cada vínculo tem seu próprio ID e preço

---

### 4.2 Cenário: Atualizar Preço de um Adicional

```typescript
// 1. Listar itens do complemento
const itens = await listarItensComplemento(complementoId);

// 2. Encontrar o vínculo do item desejado
const vinculoBacon = itens.adicionais.find(a => a.nome === "Bacon");

// 3. Atualizar preço usando o ID do vínculo
await atualizarPrecoItemComplemento(complementoId, vinculoBacon.id, {
  preco: 6.00
});
```

---

### 4.3 Cenário: Reordenar Itens

```typescript
// 1. Listar itens atuais
const itens = await listarItensComplemento(complementoId);

// 2. Definir nova ordem (ex: inverter ordem)
const novaOrdem = itens.adicionais
  .reverse()
  .map((adicional, index) => ({
    item_id: adicional.id,  // ID do vínculo
    ordem: index
  }));

// 3. Atualizar ordem
await atualizarOrdemItens(complementoId, {
  item_ordens: novaOrdem
});
```

---

## 5. Estrutura de Dados

### 5.1 ItemVinculoInput (Request)

```typescript
interface ItemVinculoInput {
  tipo: "produto" | "receita" | "combo";
  produto_cod_barras?: string;  // Obrigatório se tipo=produto
  receita_id?: number;          // Obrigatório se tipo=receita
  combo_id?: number;            // Obrigatório se tipo=combo
  ordem?: number;               // Opcional
  preco_complemento?: number;   // Opcional: preço específico
}
```

### 5.2 VincularItensComplementoRequest

```typescript
interface VincularItensComplementoRequest {
  items: ItemVinculoInput[];
  ordens?: number[];            // Opcional: sobrescreve ordem dos items
  precos?: (number | null)[];   // Opcional: sobrescreve preco_complemento dos items
}
```

### 5.3 AdicionalResponse (Response)

```typescript
interface AdicionalResponse {
  id: number;              // ID do VÍNCULO (não do produto/receita/combo)
  nome: string;
  descricao?: string;
  imagem?: string;
  preco: number;           // Preço efetivo (preco_complemento ou padrão)
  custo: number;
  ativo: boolean;
  ordem: number;
  created_at: string;
  updated_at: string;
}
```

**⚠️ IMPORTANTE:** 
- `id` = ID do **vínculo** (`complemento_vinculo_item.id`)
- `preco` = Preço **efetivo** (preço específico se definido, senão preço padrão)

---

## 6. Tratamento de Erros

### 6.1 Erros Comuns

**Erro 400: "Cada item deve ter exatamente um de: produto_cod_barras, receita_id, combo_id"**
- **Causa:** Item com múltiplos ou nenhum tipo informado
- **Solução:** Verificar que cada item tem exatamente um tipo preenchido

**Erro 404: "Complemento {id} não encontrado"**
- **Causa:** Complemento não existe
- **Solução:** Verificar se o `complemento_id` está correto

**Erro 404: "Vínculo {id} não encontrado no complemento {complemento_id}"**
- **Causa:** Tentativa de atualizar/remover vínculo que não existe
- **Solução:** Verificar se o `item_id` (ID do vínculo) está correto

**Erro 400: "Item não pertence à mesma empresa do complemento"**
- **Causa:** Tentativa de vincular item de empresa diferente
- **Solução:** Verificar que todos os itens pertencem à mesma empresa do complemento

---

## 7. Checklist de Implementação

- [ ] **Remover todas as chamadas** aos endpoints `/api/catalogo/admin/adicionais/*`
- [ ] **Migrar código** que criava/atualizava adicionais para usar vínculos de complementos
- [ ] Usar `id` do vínculo (não do produto/receita/combo) em todas as operações
- [ ] Tratar `preco` como preço efetivo (pode ser específico ou padrão)
- [ ] Permitir definir `preco_complemento` ao vincular itens
- [ ] Permitir atualizar preço de um vínculo existente
- [ ] Usar `adicional_id` = ID do vínculo ao criar pedidos/carrinho
- [ ] Tratar `ordem` corretamente (pode vir do item ou da lista `ordens`)
- [ ] Validar que cada item tem exatamente um tipo (produto/receita/combo)
- [ ] Exibir preço efetivo na interface (não assumir preço padrão)
- [ ] Testar que endpoints antigos de adicionais retornam 404 (não quebrar se chamados)

---

## 8. Resumo Rápido

### ⚠️ IMPORTANTE - Endpoints Removidos:
- **NÃO usar mais** `/api/catalogo/admin/adicionais/*` (retorna 404)
- **CRUD de adicionais foi removido** - não existe mais entidade `adicionais`
- **Usar endpoints de complementos** para vincular produtos/receitas/combos

### ✅ O que fazer:
- Usar `id` do vínculo em todas as operações (atualizar, remover, ordem)
- Usar `adicional_id` = ID do vínculo em pedidos/carrinho
- Tratar `preco` como preço efetivo (específico ou padrão)
- Permitir definir `preco_complemento` ao vincular
- Vincular produtos/receitas/combos diretamente aos complementos

### ❌ O que NÃO fazer:
- **NÃO usar endpoints de adicionais** (`/api/catalogo/admin/adicionais/*`)
- Não usar ID do produto/receita/combo em operações de vínculo
- Não assumir que o preço é sempre o padrão da entidade
- Não esquecer que cada vínculo tem seu próprio ID e preço

---

## 9. Referências

- **Endpoint Base:** `/api/catalogo/admin/complementos/{complemento_id}/itens`
- **Documentação Backend:** `DOC_CORRECAO_FLUSH_PRECO_VINCULOS.md`
- **Schema:** `schema_complemento.py` (ItemVinculoInput, VincularItensComplementoRequest)
