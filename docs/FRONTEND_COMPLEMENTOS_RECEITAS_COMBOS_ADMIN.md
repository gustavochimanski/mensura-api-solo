# 📘 Documentação Frontend: Complementos de Receitas e Combos (Admin)

## 🎯 Objetivo

Este documento fornece **tudo que o frontend precisa** para implementar a funcionalidade de gerenciamento de complementos para **Receitas** e **Combos** no painel administrativo.

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Estrutura de Dados](#estrutura-de-dados)
3. [Endpoints Disponíveis](#endpoints-disponíveis)
4. [Fluxos de Trabalho](#fluxos-de-trabalho)
5. [Exemplos Práticos](#exemplos-práticos)
6. [Validações e Regras](#validações-e-regras)
7. [Interface Sugerida](#interface-sugerida)

---

## 🏗️ Visão Geral

### Hierarquia do Sistema

```
Receita/Combo
    ↓ (vinculação N:N)
Complemento (grupo de opções)
    ↓ (vinculação N:N)
Item/Adicional (opção individual)
```

### Conceitos Fundamentais

**Complemento:**
- É um **grupo** que agrupa itens relacionados
- Exemplos: "Tamanho", "Bebida", "Adicionais", "Tipo de Pão"
- Tem configurações próprias (obrigatório, quantitativo, múltipla escolha)
- Pode ser vinculado a múltiplas receitas ou combos

**Item/Adicional:**
- É uma **opção individual** dentro de um complemento
- Exemplos: "Pequeno", "Coca-Cola", "Bacon", "Pão Francês"
- Tem preço próprio
- Pode pertencer a múltiplos complementos (com preços diferentes em cada um)

**Receita/Combo:**
- Entidades que podem ter complementos vinculados
- Cada uma tem sua própria lista de complementos disponíveis
- Os complementos são específicos para cada receita/combo

---

## 📊 Estrutura de Dados

### ComplementoResponse

```typescript
interface ComplementoResponse {
  id: number;
  empresa_id: number;
  nome: string;
  descricao: string | null;
  obrigatorio: boolean;
  quantitativo: boolean;
  minimo_itens: number | null;
  maximo_itens: number | null;
  ordem: number;
  ativo: boolean;
  adicionais: AdicionalResponse[];
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}
```

### AdicionalResponse

```typescript
interface AdicionalResponse {
  id: number;
  nome: string;
  descricao: string | null;
  preco: number;
  custo: number;
  ativo: boolean;
  ordem: number;
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}
```

### ComplementoResumidoResponse

```typescript
interface ComplementoResumidoResponse {
  id: number;
  nome: string;
  obrigatorio: boolean;
  quantitativo: boolean;
  minimo_itens: number | null;
  maximo_itens: number | null;
  ordem: number;
}
```

### Requests

#### CriarComplementoRequest

```typescript
interface CriarComplementoRequest {
  empresa_id: number;
  nome: string; // 1-100 caracteres
  descricao?: string | null; // até 255 caracteres
  obrigatorio?: boolean; // default: false
  quantitativo?: boolean; // default: false
  minimo_itens?: number | null; // >= 0, null = sem mínimo
  maximo_itens?: number | null; // >= 0, null = sem limite
  ordem?: number; // default: 0
}
```

#### AtualizarComplementoRequest

```typescript
interface AtualizarComplementoRequest {
  nome?: string;
  descricao?: string | null;
  obrigatorio?: boolean;
  quantitativo?: boolean;
  minimo_itens?: number | null;
  maximo_itens?: number | null;
  ativo?: boolean;
  ordem?: number;
}
```

#### VincularComplementosReceitaRequest

```typescript
interface VincularComplementosReceitaRequest {
  complemento_ids: number[];
}
```

#### VincularComplementosComboRequest

```typescript
interface VincularComplementosComboRequest {
  complemento_ids: number[];
}
```

#### CriarItemRequest

```typescript
interface CriarItemRequest {
  empresa_id: number;
  nome: string; // 1-100 caracteres
  descricao?: string | null; // até 255 caracteres
  preco: number; // decimal com 2 casas
  custo: number; // decimal com 2 casas
  ativo?: boolean; // default: true
}
```

#### AtualizarAdicionalRequest

```typescript
interface AtualizarAdicionalRequest {
  nome?: string;
  descricao?: string | null;
  preco?: number;
  custo?: number;
  ativo?: boolean;
  ordem?: number;
}
```

#### VincularItensComplementoRequest

```typescript
interface VincularItensComplementoRequest {
  item_ids: number[];
  ordens?: number[]; // opcional, usa índice se não informado
  precos?: number[]; // opcional, preços específicos por item neste complemento
}
```

#### VincularItemComplementoRequest

```typescript
interface VincularItemComplementoRequest {
  item_id: number;
  ordem?: number; // opcional
  preco_complemento?: number; // opcional, sobrescreve o preço padrão
}
```

#### AtualizarOrdemItensRequest

```typescript
interface AtualizarOrdemItensRequest {
  item_ids?: number[]; // IDs na ordem desejada (ordem = índice)
  item_ordens?: Array<{ // ou formato completo
    item_id: number;
    ordem: number;
  }>;
}
```

#### AtualizarPrecoItemComplementoRequest

```typescript
interface AtualizarPrecoItemComplementoRequest {
  preco: number; // decimal com 2 casas
}
```

---

## 🔌 Endpoints Disponíveis

### Base URL
```
/api/catalogo/admin
```

### Autenticação
Todos os endpoints requerem autenticação de admin (header de autenticação).

---

### 1. Gerenciamento de Complementos

#### Listar Complementos
```http
GET /api/catalogo/admin/complementos?empresa_id={empresa_id}&apenas_ativos={true|false}
```

**Query Parameters:**
- `empresa_id` (obrigatório): ID da empresa
- `apenas_ativos` (opcional, default: `true`): Filtrar apenas complementos ativos

**Response:** `ComplementoResponse[]`

---

#### Criar Complemento
```http
POST /api/catalogo/admin/complementos
```

**Body:** `CriarComplementoRequest`

**Response:** `ComplementoResponse` (201 Created)

---

#### Buscar Complemento por ID
```http
GET /api/catalogo/admin/complementos/{complemento_id}
```

**Response:** `ComplementoResponse`

---

#### Atualizar Complemento
```http
PUT /api/catalogo/admin/complementos/{complemento_id}
```

**Body:** `AtualizarComplementoRequest`

**Response:** `ComplementoResponse`

---

#### Deletar Complemento
```http
DELETE /api/catalogo/admin/complementos/{complemento_id}
```

**Response:** `{ message: "Complemento deletado com sucesso" }`

---

### 2. Vincular Complementos a Receitas

#### Vincular Complementos a Receita
```http
POST /api/catalogo/admin/complementos/receita/{receita_id}/vincular
```

**Body:** `VincularComplementosReceitaRequest`

**Response:** `VincularComplementosReceitaResponse`
```typescript
interface VincularComplementosReceitaResponse {
  receita_id: number;
  complementos_vinculados: ComplementoResumidoResponse[];
  message: string;
}
```

**Comportamento:**
- Remove todas as vinculações existentes da receita
- Cria novas vinculações com os IDs fornecidos
- Valida que todos os complementos existem e pertencem à mesma empresa

---

#### Listar Complementos de uma Receita
```http
GET /api/catalogo/admin/complementos/receita/{receita_id}?apenas_ativos={true|false}
```

**Query Parameters:**
- `apenas_ativos` (opcional, default: `true`): Filtrar apenas complementos ativos

**Response:** `ComplementoResponse[]`

---

### 3. Vincular Complementos a Combos

#### Vincular Complementos a Combo
```http
POST /api/catalogo/admin/complementos/combo/{combo_id}/vincular
```

**Body:** `VincularComplementosComboRequest`

**Response:** `VincularComplementosComboResponse`
```typescript
interface VincularComplementosComboResponse {
  combo_id: number;
  complementos_vinculados: ComplementoResumidoResponse[];
  message: string;
}
```

**Comportamento:**
- Remove todas as vinculações existentes do combo
- Cria novas vinculações com os IDs fornecidos
- Valida que todos os complementos existem e pertencem à mesma empresa do combo

---

#### Listar Complementos de um Combo
```http
GET /api/catalogo/admin/complementos/combo/{combo_id}?apenas_ativos={true|false}
```

**Query Parameters:**
- `apenas_ativos` (opcional, default: `true`): Filtrar apenas complementos ativos

**Response:** `ComplementoResponse[]`

---

### 4. Gerenciamento de Itens/Adicionais

#### Criar Item/Adicional
```http
POST /api/catalogo/admin/adicionais
```

**Body:** `CriarItemRequest`

**Response:** `AdicionalResponse` (201 Created)

---

#### Listar Itens/Adicionais
```http
GET /api/catalogo/admin/adicionais?empresa_id={empresa_id}&apenas_ativos={true|false}&search={termo}
```

**Query Parameters:**
- `empresa_id` (obrigatório): ID da empresa
- `apenas_ativos` (opcional, default: `true`): Filtrar apenas itens ativos
- `search` (opcional): Termo de busca (nome ou descrição)

**Response:** `AdicionalResponse[]`

---

#### Buscar Item/Adicional por ID
```http
GET /api/catalogo/admin/adicionais/{adicional_id}
```

**Response:** `AdicionalResponse`

---

#### Atualizar Item/Adicional
```http
PUT /api/catalogo/admin/adicionais/{adicional_id}
```

**Body:** `AtualizarAdicionalRequest`

**Response:** `AdicionalResponse`

---

#### Deletar Item/Adicional
```http
DELETE /api/catalogo/admin/adicionais/{adicional_id}
```

**Response:** `{ message: "Adicional deletado com sucesso" }`

---

### 5. Vincular Itens a Complementos

#### Vincular Múltiplos Itens a um Complemento
```http
POST /api/catalogo/admin/complementos/{complemento_id}/itens/vincular
```

**Body:** `VincularItensComplementoRequest`

**Response:** `VincularItensComplementoResponse`
```typescript
interface VincularItensComplementoResponse {
  complemento_id: number;
  itens_vinculados: AdicionalResponse[];
  message: string;
}
```

**Comportamento:**
- Remove todas as vinculações existentes do complemento
- Cria novas vinculações com os IDs fornecidos
- Valida que todos os itens e o complemento pertencem à mesma empresa

---

#### Adicionar um Item a um Complemento
```http
POST /api/catalogo/admin/complementos/{complemento_id}/itens/adicionar
```

**Body:** `VincularItemComplementoRequest`

**Response:** `VincularItemComplementoResponse`
```typescript
interface VincularItemComplementoResponse {
  complemento_id: number;
  item_vinculado: AdicionalResponse;
  message: string;
}
```

**Comportamento:**
- Se o item já estiver vinculado, atualiza ordem e/ou preço
- Se não estiver vinculado, cria nova vinculação

---

#### Listar Itens de um Complemento
```http
GET /api/catalogo/admin/complementos/{complemento_id}/itens?apenas_ativos={true|false}
```

**Query Parameters:**
- `apenas_ativos` (opcional, default: `true`): Filtrar apenas itens ativos

**Response:** `AdicionalResponse[]`

---

#### Desvincular Item de um Complemento
```http
DELETE /api/catalogo/admin/complementos/{complemento_id}/itens/{item_id}
```

**Response:** `{ message: "Item desvinculado com sucesso" }`

---

#### Atualizar Ordem dos Itens
```http
PUT /api/catalogo/admin/complementos/{complemento_id}/itens/ordem
```

**Body:** `AtualizarOrdemItensRequest`

**Response:** `{ message: "Ordem dos itens atualizada com sucesso" }`

---

#### Atualizar Preço de Item em um Complemento
```http
PUT /api/catalogo/admin/complementos/{complemento_id}/itens/{item_id}/preco
```

**Body:** `AtualizarPrecoItemComplementoRequest`

**Response:** `AdicionalResponse`

**Observação:** Este endpoint atualiza apenas o preço do item **dentro deste complemento específico**. Não altera o preço padrão do item.

---

## 🔄 Fluxos de Trabalho

### Fluxo 1: Criar e Vincular Complementos a uma Receita

1. **Listar complementos disponíveis da empresa**
   ```
   GET /api/catalogo/admin/complementos?empresa_id={empresa_id}&apenas_ativos=false
   ```

2. **Se necessário, criar novos complementos**
   ```
   POST /api/catalogo/admin/complementos
   Body: CriarComplementoRequest
   ```

3. **Se necessário, criar/adicionar itens aos complementos**
   ```
   POST /api/catalogo/admin/adicionais (criar item)
   POST /api/catalogo/admin/complementos/{complemento_id}/itens/adicionar (vincular item)
   ```

4. **Vincular complementos à receita**
   ```
   POST /api/catalogo/admin/complementos/receita/{receita_id}/vincular
   Body: { complemento_ids: [1, 2, 3] }
   ```

5. **Verificar complementos vinculados**
   ```
   GET /api/catalogo/admin/complementos/receita/{receita_id}
   ```

---

### Fluxo 2: Criar e Vincular Complementos a um Combo

1. **Listar complementos disponíveis da empresa**
   ```
   GET /api/catalogo/admin/complementos?empresa_id={empresa_id}&apenas_ativos=false
   ```

2. **Se necessário, criar novos complementos**
   ```
   POST /api/catalogo/admin/complementos
   Body: CriarComplementoRequest
   ```

3. **Se necessário, criar/adicionar itens aos complementos**
   ```
   POST /api/catalogo/admin/adicionais (criar item)
   POST /api/catalogo/admin/complementos/{complemento_id}/itens/adicionar (vincular item)
   ```

4. **Vincular complementos ao combo**
   ```
   POST /api/catalogo/admin/complementos/combo/{combo_id}/vincular
   Body: { complemento_ids: [1, 2, 3] }
   ```

5. **Verificar complementos vinculados**
   ```
   GET /api/catalogo/admin/complementos/combo/{combo_id}
   ```

---

### Fluxo 3: Gerenciar Itens de um Complemento

1. **Listar itens disponíveis da empresa**
   ```
   GET /api/catalogo/admin/adicionais?empresa_id={empresa_id}&apenas_ativos=false
   ```

2. **Criar novo item (se necessário)**
   ```
   POST /api/catalogo/admin/adicionais
   Body: CriarItemRequest
   ```

3. **Vincular múltiplos itens ao complemento**
   ```
   POST /api/catalogo/admin/complementos/{complemento_id}/itens/vincular
   Body: {
     item_ids: [1, 2, 3],
     ordens: [0, 1, 2], // opcional
     precos: [5.00, 7.50, 10.00] // opcional, preços específicos
   }
   ```

4. **Ou adicionar um item por vez**
   ```
   POST /api/catalogo/admin/complementos/{complemento_id}/itens/adicionar
   Body: {
     item_id: 1,
     ordem: 0, // opcional
     preco_complemento: 5.00 // opcional
   }
   ```

5. **Atualizar ordem dos itens (arrastar e soltar)**
   ```
   PUT /api/catalogo/admin/complementos/{complemento_id}/itens/ordem
   Body: {
     item_ids: [3, 1, 2] // nova ordem
   }
   ```

6. **Atualizar preço de um item específico no complemento**
   ```
   PUT /api/catalogo/admin/complementos/{complemento_id}/itens/{item_id}/preco
   Body: { preco: 8.50 }
   ```

---

## 💡 Exemplos Práticos

### Exemplo 1: Criar Complemento "Tamanho" para Receita

```typescript
// 1. Criar o complemento
const criarComplemento = async () => {
  const response = await fetch('/api/catalogo/admin/complementos', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      // ... headers de autenticação
    },
    body: JSON.stringify({
      empresa_id: 1,
      nome: 'Tamanho',
      descricao: 'Escolha o tamanho da pizza',
      obrigatorio: true,
      quantitativo: false,
      minimo_itens: 1,
      maximo_itens: 1,
      ordem: 1
    })
  });
  return response.json();
};

// 2. Criar itens do complemento
const criarItens = async () => {
  const itens = [
    { empresa_id: 1, nome: 'Pequena', preco: 0, custo: 0 },
    { empresa_id: 1, nome: 'Média', preco: 5.00, custo: 2.00 },
    { empresa_id: 1, nome: 'Grande', preco: 10.00, custo: 4.00 }
  ];
  
  const itensCriados = [];
  for (const item of itens) {
    const response = await fetch('/api/catalogo/admin/adicionais', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(item)
    });
    itensCriados.push(await response.json());
  }
  return itensCriados;
};

// 3. Vincular itens ao complemento
const vincularItens = async (complementoId: number, itemIds: number[]) => {
  const response = await fetch(
    `/api/catalogo/admin/complementos/${complementoId}/itens/vincular`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        item_ids: itemIds,
        ordens: [0, 1, 2] // ordem de exibição
      })
    }
  );
  return response.json();
};

// 4. Vincular complemento à receita
const vincularComplementoReceita = async (receitaId: number, complementoId: number) => {
  const response = await fetch(
    `/api/catalogo/admin/complementos/receita/${receitaId}/vincular`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        complemento_ids: [complementoId]
      })
    }
  );
  return response.json();
};
```

---

### Exemplo 2: Vincular Múltiplos Complementos a um Combo

```typescript
const vincularComplementosCombo = async (
  comboId: number,
  complementoIds: number[]
) => {
  const response = await fetch(
    `/api/catalogo/admin/complementos/combo/${comboId}/vincular`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        complemento_ids: complementoIds
      })
    }
  );
  return response.json();
};

// Uso:
await vincularComplementosCombo(123, [1, 2, 3]); // Vincula complementos 1, 2 e 3 ao combo 123
```

---

### Exemplo 3: Listar e Exibir Complementos de uma Receita

```typescript
const listarComplementosReceita = async (receitaId: number) => {
  const response = await fetch(
    `/api/catalogo/admin/complementos/receita/${receitaId}?apenas_ativos=true`
  );
  return response.json();
};

// Uso:
const complementos = await listarComplementosReceita(456);

// Estrutura retornada:
// [
//   {
//     id: 1,
//     nome: "Tamanho",
//     obrigatorio: true,
//     quantitativo: false,
//     minimo_itens: 1,
//     maximo_itens: 1,
//     ordem: 1,
//     adicionais: [
//       { id: 1, nome: "Pequena", preco: 0, ordem: 0 },
//       { id: 2, nome: "Média", preco: 5.00, ordem: 1 },
//       { id: 3, nome: "Grande", preco: 10.00, ordem: 2 }
//     ]
//   },
//   {
//     id: 2,
//     nome: "Bebida",
//     obrigatorio: false,
//     quantitativo: true,
//     minimo_itens: 0,
//     maximo_itens: null,
//     ordem: 2,
//     adicionais: [
//       { id: 4, nome: "Coca-Cola", preco: 4.50, ordem: 0 },
//       { id: 5, nome: "Pepsi", preco: 4.50, ordem: 1 }
//     ]
//   }
// ]
```

---

## ⚠️ Validações e Regras

### Regras de Negócio

1. **Empresa:**
   - Todos os complementos e itens devem pertencer à mesma empresa
   - Ao vincular complementos a receitas/combos, o sistema valida que todos pertencem à mesma empresa

2. **Vinculação de Complementos:**
   - Ao vincular complementos a uma receita/combo, **todas as vinculações anteriores são removidas**
   - A nova lista de `complemento_ids` substitui completamente a anterior
   - Para manter complementos existentes e adicionar novos, você deve incluir todos os IDs (antigos + novos)

3. **Vinculação de Itens:**
   - Ao vincular itens a um complemento usando `/itens/vincular`, **todas as vinculações anteriores são removidas**
   - A nova lista de `item_ids` substitui completamente a anterior
   - Para manter itens existentes e adicionar novos, você deve incluir todos os IDs (antigos + novos)

4. **Preços:**
   - Cada item tem um preço padrão
   - Um item pode ter preço diferente em cada complemento (usando `preco_complemento`)
   - O campo `preco` no `AdicionalResponse` retorna o preço efetivo no contexto do complemento

5. **Ordem:**
   - Complementos e itens têm ordem de exibição
   - A ordem pode ser atualizada independentemente
   - Use `item_ids` na ordem desejada ou `item_ordens` com ordem explícita

6. **Ativo/Inativo:**
   - Complementos e itens podem ser ativados/desativados
   - Ao listar, use `apenas_ativos=true` para filtrar apenas os ativos
   - Complementos/itens inativos ainda podem ser vinculados, mas não aparecem nas listagens públicas

### Validações do Frontend

1. **Antes de vincular complementos:**
   - Verificar se todos os complementos existem
   - Verificar se todos pertencem à mesma empresa da receita/combo
   - Mostrar mensagem de erro se algum complemento não for encontrado

2. **Antes de vincular itens:**
   - Verificar se todos os itens existem
   - Verificar se todos pertencem à mesma empresa do complemento
   - Mostrar mensagem de erro se algum item não for encontrado

3. **Ao criar/atualizar complemento:**
   - Validar que `minimo_itens <= maximo_itens` (se ambos não forem null)
   - Validar que `minimo_itens >= 0` e `maximo_itens >= 0` (se não forem null)
   - Validar tamanho do nome (1-100 caracteres)
   - Validar tamanho da descrição (até 255 caracteres)

4. **Ao criar/atualizar item:**
   - Validar que preço e custo são números positivos
   - Validar tamanho do nome (1-100 caracteres)
   - Validar tamanho da descrição (até 255 caracteres)

---

## 🎨 Interface Sugerida

### Tela de Gerenciamento de Complementos (Receita/Combo)

```
┌─────────────────────────────────────────────────────────────┐
│ Receita: Pizza Margherita                    [Salvar]       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Complementos Vinculados:                                    │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐ │
│ │ [1] Tamanho (Obrigatório)                    [↑] [↓] │ │
│ │     Mín: 1 | Máx: 1 | Quantitativo: Não              │ │
│ │     Itens: Pequena (R$ 0,00), Média (R$ 5,00), ...    │ │
│ │     [Editar] [Remover]                                 │ │
│ └───────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐ │
│ │ [2] Bebida (Opcional)                         [↑] [↓] │ │
│ │     Mín: 0 | Máx: Sem limite | Quantitativo: Sim     │ │
│ │     Itens: Coca-Cola (R$ 4,50), Pepsi (R$ 4,50), ...  │ │
│ │     [Editar] [Remover]                                 │ │
│ └───────────────────────────────────────────────────────┘ │
│                                                             │
│ [+ Adicionar Complemento]                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Modal de Seleção de Complementos

```
┌─────────────────────────────────────────────────────────────┐
│ Selecionar Complementos                                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Buscar: [________________________]                          │
│                                                             │
│ ☑ Tamanho                                                    │
│   Mín: 1 | Máx: 1 | Obrigatório: Sim                       │
│                                                             │
│ ☐ Bebida                                                     │
│   Mín: 0 | Máx: Sem limite | Obrigatório: Não              │
│                                                             │
│ ☐ Adicionais                                                 │
│   Mín: 0 | Máx: 3 | Obrigatório: Não                        │
│                                                             │
│ [Cancelar] [Confirmar (2 selecionados)]                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Modal de Edição de Complemento

```
┌─────────────────────────────────────────────────────────────┐
│ Editar Complemento: Tamanho                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Nome: [Tamanho________________]                             │
│ Descrição: [Escolha o tamanho da pizza___]                 │
│                                                             │
│ ☑ Obrigatório                                               │
│ ☐ Quantitativo (permite quantidade e múltipla escolha)     │
│                                                             │
│ Mínimo de itens: [1] (0 = sem mínimo)                      │
│ Máximo de itens: [1] (vazio = sem limite)                   │
│                                                             │
│ Ordem: [1]                                                  │
│                                                             │
│ Itens do Complemento:                                       │
│ ┌───────────────────────────────────────────────────────┐ │
│ │ [0] Pequena - R$ 0,00                        [↑] [↓] │ │
│ │     [Editar Preço] [Remover]                          │ │
│ └───────────────────────────────────────────────────────┘ │
│ ┌───────────────────────────────────────────────────────┐ │
│ │ [1] Média - R$ 5,00                           [↑] [↓] │ │
│ │     [Editar Preço] [Remover]                          │ │
│ └───────────────────────────────────────────────────────┘ │
│                                                             │
│ [+ Adicionar Item]                                          │
│                                                             │
│ [Cancelar] [Salvar]                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Notas Importantes

1. **Substituição Completa:**
   - Ao vincular complementos ou itens, a lista anterior é **completamente substituída**
   - Sempre inclua todos os IDs que deseja manter + os novos

2. **Preços Específicos:**
   - Um item pode ter preço diferente em cada complemento
   - Use `preco_complemento` ao vincular ou o endpoint específico de atualização de preço

3. **Ordem:**
   - A ordem é importante para a exibição no frontend
   - Permita arrastar e soltar para reordenar
   - Atualize a ordem após cada mudança

4. **Validação de Empresa:**
   - O backend valida automaticamente que todos os recursos pertencem à mesma empresa
   - Não é necessário validar no frontend, mas é bom mostrar mensagens de erro amigáveis

5. **Performance:**
   - Ao listar complementos de uma receita/combo, os itens já vêm incluídos
   - Não é necessário fazer chamadas adicionais para buscar itens

---

## 🔗 Endpoints Alternativos

### Endpoint Alternativo para Receitas

Além do endpoint específico de complementos, existe também um endpoint no router de receitas:

```http
PUT /api/catalogo/admin/receitas/{receita_id}/complementos
```

Este endpoint faz a mesma coisa que:
```http
POST /api/catalogo/admin/complementos/receita/{receita_id}/vincular
```

Use qualquer um dos dois, ambos funcionam da mesma forma.

---

## ✅ Checklist de Implementação

- [ ] Criar interface para listar complementos de uma receita/combo
- [ ] Criar interface para vincular complementos a receita/combo
- [ ] Criar interface para gerenciar complementos (CRUD)
- [ ] Criar interface para gerenciar itens/adicionais (CRUD)
- [ ] Criar interface para vincular itens a complementos
- [ ] Implementar reordenação de complementos (arrastar e soltar)
- [ ] Implementar reordenação de itens (arrastar e soltar)
- [ ] Implementar edição de preço específico por complemento
- [ ] Implementar validações do frontend
- [ ] Implementar tratamento de erros
- [ ] Implementar feedback visual (loading, sucesso, erro)
- [ ] Testar todos os fluxos de trabalho
- [ ] Testar validações e regras de negócio

---

## 📞 Suporte

Em caso de dúvidas sobre a implementação, consulte:
- `docs/DOC_COMPLEMENTOS_RELACIONAMENTOS_CHECKOUT.md` - Documentação técnica completa
- `docs/MIGRACAO_FRONTEND_COMPLEMENTOS.md` - Guia de migração
- Código fonte: `app/api/catalogo/router/admin/router_complementos.py`
- Código fonte: `app/api/catalogo/services/service_complemento.py`

---

**Última atualização:** 2024

