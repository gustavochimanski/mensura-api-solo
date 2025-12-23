# 📘 Documentação Completa: Produtos, Receitas, Combos e Complementos para Admin - Aba Pedidos

## 🎯 Objetivo

Este documento fornece **tudo que o frontend admin precisa** para implementar a criação, manipulação e gerenciamento de:
- **Produtos**
- **Receitas**
- **Combos Unificados**
- **Complementos** (vinculados a produtos, receitas e combos)

Tudo isso integrado para uso na **aba de pedidos**.

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Autenticação](#autenticação)
3. [Produtos - CRUD Completo](#produtos---crud-completo)
4. [Receitas - CRUD Completo](#receitas---crud-completo)
5. [Combos - CRUD Completo](#combos---crud-completo)
6. [Complementos - CRUD e Vinculação](#complementos---crud-e-vinculação)
7. [Integração com Pedidos](#integração-com-pedidos)
8. [Estruturas de Dados](#estruturas-de-dados)
9. [Fluxos de Trabalho Completos](#fluxos-de-trabalho-completos)
10. [Exemplos Práticos](#exemplos-práticos)

---

## 🏗️ Visão Geral

### Hierarquia do Sistema

```
Empresa
  ├─ Produtos (cod_barras)
  │   └─ Complementos (N:N)
  │       └─ Itens/Adicionais (N:N)
  ├─ Receitas (id)
  │   ├─ Ingredientes (N:N)
  │   └─ Complementos (N:N)
  │       └─ Itens/Adicionais (N:N)
  └─ Combos (id)
      ├─ Itens do Combo (produtos com quantidade)
      └─ Complementos (N:N)
          └─ Itens/Adicionais (N:N)
```

### Conceitos Fundamentais

**Produto:**
- Identificado por `cod_barras` (string)
- Pode ter complementos vinculados
- Preço e disponibilidade por empresa

**Receita:**
- Identificada por `id` (integer)
- Produto composto com ingredientes
- Pode ter complementos vinculados
- Preço e disponibilidade por empresa

**Combo:**
- Identificado por `id` (integer)
- Agrupa múltiplos produtos com quantidades
- Pode ter complementos vinculados
- Preço total do combo

**Complemento:**
- Grupo de opções (ex: "Tamanho", "Bebida", "Adicionais")
- Vinculado a produtos, receitas ou combos (N:N)
- Tem configurações (obrigatório, quantitativo, limites)

**Item/Adicional:**
- Opção individual dentro de um complemento
- Tem preço próprio
- Pode ter preço diferente em cada complemento

---

## 🔐 Autenticação

Todos os endpoints requerem autenticação via Bearer Token:

```http
Authorization: Bearer {access_token}
```

O token é obtido através do endpoint de login admin.

**Base URL:** `/api/catalogo/admin`

---

## 📦 Produtos - CRUD Completo

### Base URL
```
/api/catalogo/admin/produtos
```

### 1. Listar Produtos

**GET** `/api/catalogo/admin/produtos/`

**Query Parameters:**
- `cod_empresa` (obrigatório): ID da empresa
- `page` (opcional, default: 1): Número da página
- `limit` (opcional, default: 30, max: 100): Itens por página
- `apenas_disponiveis` (opcional, default: false): Filtrar apenas disponíveis
- `search` (opcional): Termo de busca (código de barras, descrição ou SKU)

**Response:** `200 OK`
```json
{
  "data": [
    {
      "cod_barras": "7891234567890",
      "descricao": "Hambúrguer Artesanal",
      "imagem": "https://storage.exemplo.com/produtos/uuid.jpg",
      "preco_venda": 25.90,
      "custo": 10.50,
      "disponivel": true,
      "exibir_delivery": true,
      "tem_receita": false
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 30,
  "has_more": true
}
```

---

### 2. Criar Produto

**POST** `/api/catalogo/admin/produtos/`

**Content-Type:** `multipart/form-data`

**Parâmetros (Form Data):**
- `cod_empresa` (obrigatório): ID da empresa
- `cod_barras` (opcional): Código de barras (gerado automaticamente se não fornecido)
- `descricao` (obrigatório): Descrição do produto (1-255 caracteres)
- `preco_venda` (obrigatório): Preço de venda (Decimal, > 0)
- `custo` (opcional): Custo do produto (Decimal)
- `data_cadastro` (opcional): Data de cadastro (YYYY-MM-DD)
- `imagem` (opcional): Arquivo de imagem (JPEG, PNG, WebP)

**Response:** `200 OK`
```json
{
  "produto": {
    "cod_barras": "7891234567890",
    "descricao": "Hambúrguer Artesanal",
    "imagem": "https://storage.exemplo.com/produtos/uuid.jpg",
    "ativo": true,
    "unidade_medida": "UN",
    "tem_receita": false,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  },
  "produto_emp": {
    "empresa_id": 1,
    "cod_barras": "7891234567890",
    "preco_venda": 25.90,
    "custo": 10.50,
    "disponivel": true,
    "exibir_delivery": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

**Exemplo JavaScript:**
```typescript
const formData = new FormData();
formData.append('cod_empresa', '1');
formData.append('descricao', 'Hambúrguer Artesanal');
formData.append('preco_venda', '25.90');
formData.append('custo', '10.50');
if (imagemFile) {
  formData.append('imagem', imagemFile);
}

const response = await fetch('/api/catalogo/admin/produtos/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
  },
  body: formData,
});
```

---

### 3. Atualizar Produto

**PUT** `/api/catalogo/admin/produtos/{cod_barras}`

**Content-Type:** `multipart/form-data`

**Parâmetros (Form Data - todos opcionais):**
- `cod_empresa` (obrigatório): ID da empresa
- `descricao` (opcional): Descrição do produto
- `preco_venda` (opcional): Preço de venda
- `custo` (opcional): Custo do produto
- `sku_empresa` (opcional): SKU da empresa
- `disponivel` (opcional): Se está disponível
- `exibir_delivery` (opcional): Se exibe no delivery
- `ativo` (opcional): Se está ativo
- `unidade_medida` (opcional): Unidade de medida
- `imagem` (opcional): Nova imagem

**Response:** `200 OK` (mesmo formato do criar)

---

### 4. Deletar Produto

**DELETE** `/api/catalogo/admin/produtos/{cod_barras}`

**Query Parameters:**
- `empresa_id` (obrigatório): ID da empresa

**Response:** `204 No Content`

---

## 🍕 Receitas - CRUD Completo

### Base URL
```
/api/catalogo/admin/receitas
```

### 1. Listar Receitas

**GET** `/api/catalogo/admin/receitas/`

**Query Parameters:**
- `empresa_id` (opcional): Filtrar por empresa
- `ativo` (opcional): Filtrar por status ativo (true/false)
- `search` (opcional): Termo de busca em nome/descrição

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "empresa_id": 1,
    "nome": "Pizza Margherita",
    "descricao": "Pizza tradicional italiana",
    "preco_venda": 45.90,
    "custo_total": 15.50,
    "imagem": "https://exemplo.com/pizza.jpg",
    "ativo": true,
    "disponivel": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### 2. Criar Receita

**POST** `/api/catalogo/admin/receitas/`

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "empresa_id": 1,
  "nome": "Pizza Margherita",
  "descricao": "Pizza tradicional italiana",
  "preco_venda": 45.90,
  "imagem": "https://exemplo.com/pizza.jpg",
  "ativo": true,
  "disponivel": true
}
```

**Response:** `201 Created` (mesmo formato do listar)

---

### 3. Buscar Receita por ID

**GET** `/api/catalogo/admin/receitas/{receita_id}`

**Response:** `200 OK` (mesmo formato do listar)

---

### 4. Atualizar Receita

**PUT** `/api/catalogo/admin/receitas/{receita_id}`

**Content-Type:** `application/json`

**Request Body:** (todos os campos são opcionais)
```json
{
  "nome": "Pizza Margherita Especial",
  "descricao": "Pizza tradicional italiana com ingredientes premium",
  "preco_venda": 49.90,
  "imagem": "https://exemplo.com/pizza-premium.jpg",
  "ativo": true,
  "disponivel": true
}
```

**Response:** `200 OK` (mesmo formato do listar)

---

### 5. Deletar Receita

**DELETE** `/api/catalogo/admin/receitas/{receita_id}`

**Response:** `204 No Content`

---

### 6. Gerenciar Ingredientes da Receita

#### Listar Ingredientes
**GET** `/api/catalogo/admin/receitas/{receita_id}/ingredientes`

#### Adicionar Ingrediente
**POST** `/api/catalogo/admin/receitas/ingredientes`
```json
{
  "receita_id": 1,
  "ingrediente_id": 5,
  "quantidade": 500.0
}
```

#### Atualizar Quantidade
**PUT** `/api/catalogo/admin/receitas/ingredientes/{receita_ingrediente_id}`
```json
{
  "quantidade": 600.0
}
```

#### Remover Ingrediente
**DELETE** `/api/catalogo/admin/receitas/ingredientes/{receita_ingrediente_id}`

---

## 🎁 Combos - CRUD Completo

### Base URL
```
/api/catalogo/admin/combos
```

### 1. Listar Combos

**GET** `/api/catalogo/admin/combos/`

**Query Parameters:**
- `cod_empresa` (obrigatório): ID da empresa
- `page` (opcional, default: 1): Número da página
- `limit` (opcional, default: 30, max: 100): Itens por página
- `search` (opcional): Termo de busca no título/descrição

**Response:** `200 OK`
```json
{
  "data": [
    {
      "id": 1,
      "empresa_id": 1,
      "titulo": "Combo Pizza + Refrigerante",
      "descricao": "Pizza grande + 2 litros de refrigerante",
      "preco_total": 59.90,
      "custo_total": 25.50,
      "ativo": true,
      "imagem": "https://storage.exemplo.com/combos/uuid.jpg",
      "itens": [
        {
          "produto_cod_barras": "7891234567890",
          "quantidade": 1
        },
        {
          "produto_cod_barras": "7891234567891",
          "quantidade": 2
        }
      ],
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "limit": 30,
  "has_more": true
}
```

---

### 2. Criar Combo

**POST** `/api/catalogo/admin/combos/`

**Content-Type:** `multipart/form-data`

**Parâmetros (Form Data):**
- `empresa_id` (obrigatório): ID da empresa
- `titulo` (obrigatório): Título do combo (1-120 caracteres)
- `descricao` (obrigatório): Descrição do combo (1-255 caracteres)
- `preco_total` (obrigatório): Preço total do combo (>= 0)
- `ativo` (opcional, default: true): Status ativo
- `itens` (obrigatório): JSON string com array de itens
- `imagem` (opcional): Arquivo de imagem

**Formato do JSON `itens`:**
```json
[
  {
    "produto_cod_barras": "7891234567890",
    "quantidade": 1
  },
  {
    "produto_cod_barras": "7891234567891",
    "quantidade": 2
  }
]
```

**Exemplo JavaScript:**
```typescript
const formData = new FormData();
formData.append('empresa_id', '1');
formData.append('titulo', 'Combo Pizza + Refrigerante');
formData.append('descricao', 'Pizza grande + 2 litros de refrigerante');
formData.append('preco_total', '59.90');
formData.append('ativo', 'true');
formData.append('itens', JSON.stringify([
  { produto_cod_barras: '7891234567890', quantidade: 1 },
  { produto_cod_barras: '7891234567891', quantidade: 2 }
]));
if (imagemFile) {
  formData.append('imagem', imagemFile);
}

const response = await fetch('/api/catalogo/admin/combos/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
  },
  body: formData,
});
```

**Response:** `201 Created` (mesmo formato do listar)

---

### 3. Buscar Combo por ID

**GET** `/api/catalogo/admin/combos/{combo_id}`

**Response:** `200 OK` (mesmo formato do listar)

---

### 4. Atualizar Combo

**PUT** `/api/catalogo/admin/combos/{combo_id}`

**Content-Type:** `multipart/form-data`

**Parâmetros (Form Data - todos opcionais):**
- `titulo` (opcional): Título do combo
- `descricao` (opcional): Descrição do combo
- `preco_total` (opcional): Preço total do combo
- `ativo` (opcional): Status ativo
- `itens` (opcional): JSON string com array de itens (substitui TODOS os itens)
- `imagem` (opcional): Nova imagem

**⚠️ Importante:** Se `itens` for enviado, **TODOS** os itens existentes serão **substituídos** pelos novos.

**Response:** `200 OK` (mesmo formato do listar)

---

### 5. Deletar Combo

**DELETE** `/api/catalogo/admin/combos/{combo_id}`

**Response:** `204 No Content`

---

## 🎨 Complementos - CRUD e Vinculação

### Base URL
```
/api/catalogo/admin/complementos
```

### 1. Gerenciamento de Complementos

#### Listar Complementos
**GET** `/api/catalogo/admin/complementos?empresa_id={empresa_id}&apenas_ativos={true|false}`

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "empresa_id": 1,
    "nome": "Tamanho",
    "descricao": "Escolha o tamanho da pizza",
    "obrigatorio": true,
    "quantitativo": false,
    "minimo_itens": 1,
    "maximo_itens": 1,
    "ordem": 0,
    "ativo": true,
    "adicionais": [
      {
        "id": 10,
        "nome": "Pequena",
        "descricao": "30cm",
        "preco": 0.00,
        "custo": 0.00,
        "ativo": true,
        "ordem": 0,
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
      }
    ],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

#### Criar Complemento
**POST** `/api/catalogo/admin/complementos`
```json
{
  "empresa_id": 1,
  "nome": "Tamanho",
  "descricao": "Escolha o tamanho da pizza",
  "obrigatorio": true,
  "quantitativo": false,
  "minimo_itens": 1,
  "maximo_itens": 1,
  "ordem": 0
}
```

#### Buscar Complemento por ID
**GET** `/api/catalogo/admin/complementos/{complemento_id}`

#### Atualizar Complemento
**PUT** `/api/catalogo/admin/complementos/{complemento_id}`
```json
{
  "nome": "Tamanho Atualizado",
  "obrigatorio": false,
  "minimo_itens": 0,
  "maximo_itens": null
}
```

#### Deletar Complemento
**DELETE** `/api/catalogo/admin/complementos/{complemento_id}`

---

### 2. Gerenciamento de Itens/Adicionais

#### Listar Itens/Adicionais
**GET** `/api/catalogo/admin/adicionais?empresa_id={empresa_id}&apenas_ativos={true|false}&search={termo}`

#### Criar Item/Adicional
**POST** `/api/catalogo/admin/adicionais`
```json
{
  "empresa_id": 1,
  "nome": "Bacon",
  "descricao": "Bacon crocante",
  "preco": 5.00,
  "custo": 2.00,
  "ativo": true
}
```

#### Buscar Item por ID
**GET** `/api/catalogo/admin/adicionais/{adicional_id}`

#### Atualizar Item
**PUT** `/api/catalogo/admin/adicionais/{adicional_id}`
```json
{
  "nome": "Bacon Premium",
  "preco": 6.00,
  "custo": 2.50
}
```

#### Deletar Item
**DELETE** `/api/catalogo/admin/adicionais/{adicional_id}`

---

### 3. Vincular Complementos a Produtos

#### Vincular Complementos a Produto
**POST** `/api/catalogo/admin/complementos/produto/{cod_barras}/vincular`
```json
{
  "complemento_ids": [1, 2, 3]
}
```

**⚠️ Importante:** Remove todas as vinculações existentes e cria novas.

#### Listar Complementos de um Produto
**GET** `/api/catalogo/admin/complementos/produto/{cod_barras}?apenas_ativos={true|false}`

---

### 4. Vincular Complementos a Receitas

#### Vincular Complementos a Receita
**POST** `/api/catalogo/admin/complementos/receita/{receita_id}/vincular`
```json
{
  "complemento_ids": [1, 2, 3]
}
```

**Alternativa:**
**PUT** `/api/catalogo/admin/receitas/{receita_id}/complementos`
```json
{
  "complemento_ids": [1, 2, 3]
}
```

#### Listar Complementos de uma Receita
**GET** `/api/catalogo/admin/complementos/receita/{receita_id}?apenas_ativos={true|false}`

---

### 5. Vincular Complementos a Combos

#### Vincular Complementos a Combo
**POST** `/api/catalogo/admin/complementos/combo/{combo_id}/vincular`
```json
{
  "complemento_ids": [1, 2, 3]
}
```

#### Listar Complementos de um Combo
**GET** `/api/catalogo/admin/complementos/combo/{combo_id}?apenas_ativos={true|false}`

---

### 6. Vincular Itens a Complementos

#### Vincular Múltiplos Itens a um Complemento
**POST** `/api/catalogo/admin/complementos/{complemento_id}/itens/vincular`
```json
{
  "item_ids": [1, 2, 3],
  "ordens": [0, 1, 2],
  "precos": [5.00, 7.50, 10.00]
}
```

**⚠️ Importante:** Remove todas as vinculações existentes e cria novas.

#### Adicionar um Item a um Complemento
**POST** `/api/catalogo/admin/complementos/{complemento_id}/itens/adicionar`
```json
{
  "item_id": 1,
  "ordem": 0,
  "preco_complemento": 5.00
}
```

#### Listar Itens de um Complemento
**GET** `/api/catalogo/admin/complementos/{complemento_id}/itens?apenas_ativos={true|false}`

#### Desvincular Item de um Complemento
**DELETE** `/api/catalogo/admin/complementos/{complemento_id}/itens/{item_id}`

#### Atualizar Ordem dos Itens
**PUT** `/api/catalogo/admin/complementos/{complemento_id}/itens/ordem`
```json
{
  "item_ids": [3, 1, 2]
}
```

#### Atualizar Preço de Item em um Complemento
**PUT** `/api/catalogo/admin/complementos/{complemento_id}/itens/{item_id}/preco`
```json
{
  "preco": 8.50
}
```

---

## 🛒 Integração com Pedidos

### Estrutura de Item no Pedido

Quando um produto, receita ou combo é adicionado a um pedido, ele pode incluir complementos selecionados:

#### Produto no Pedido
```json
{
  "produto_cod_barras": "7891234567890",
  "quantidade": 2,
  "complementos": [
    {
      "complemento_id": 1,
      "adicionais": [
        {
          "adicional_id": 10,
          "quantidade": 1
        }
      ]
    }
  ],
  "observacao": "Sem cebola"
}
```

#### Receita no Pedido
```json
{
  "receita_id": 1,
  "quantidade": 1,
  "complementos": [
    {
      "complemento_id": 1,
      "adicionais": [
        {
          "adicional_id": 10,
          "quantidade": 1
        }
      ]
    }
  ],
  "observacao": "Bem assada"
}
```

#### Combo no Pedido
```json
{
  "combo_id": 1,
  "quantidade": 1,
  "complementos": [
    {
      "complemento_id": 1,
      "adicionais": [
        {
          "adicional_id": 10,
          "quantidade": 1
        }
      ]
    }
  ],
  "observacao": "Combo para viagem"
}
```

### Endpoints de Pedidos

#### Adicionar Produto Genérico ao Pedido
**POST** `/api/pedidos/{tipo}/pedidos/{pedido_id}/adicionar-produto`

Onde `{tipo}` pode ser: `delivery`, `mesa`, `balcao`

**Request Body:**
```json
{
  "tipo": "produto", // ou "receita" ou "combo"
  "identificador": "7891234567890", // cod_barras para produto, id para receita/combo
  "quantidade": 2,
  "complementos": [
    {
      "complemento_id": 1,
      "adicionais": [
        {
          "adicional_id": 10,
          "quantidade": 1
        }
      ]
    }
  ],
  "observacao": "Sem cebola"
}
```

---

## 📊 Estruturas de Dados

### Produto
```typescript
interface Produto {
  cod_barras: string;
  descricao: string;
  imagem?: string | null;
  ativo: boolean;
  unidade_medida?: string | null;
  tem_receita: boolean;
  created_at: string;
  updated_at: string;
}

interface ProdutoEmp {
  empresa_id: number;
  cod_barras: string;
  preco_venda: number;
  custo?: number | null;
  sku_empresa?: string | null;
  disponivel: boolean;
  exibir_delivery: boolean;
  created_at: string;
  updated_at: string;
}
```

### Receita
```typescript
interface Receita {
  id: number;
  empresa_id: number;
  nome: string;
  descricao?: string | null;
  preco_venda: number;
  custo_total: number; // Calculado automaticamente
  imagem?: string | null;
  ativo: boolean;
  disponivel: boolean;
  created_at: string;
  updated_at: string;
}
```

### Combo
```typescript
interface Combo {
  id: number;
  empresa_id: number;
  titulo: string;
  descricao: string;
  preco_total: number;
  custo_total?: number | null;
  ativo: boolean;
  imagem?: string | null;
  itens: ComboItem[];
  created_at: string;
  updated_at: string;
}

interface ComboItem {
  produto_cod_barras: string;
  quantidade: number;
}
```

### Complemento
```typescript
interface Complemento {
  id: number;
  empresa_id: number;
  nome: string;
  descricao?: string | null;
  obrigatorio: boolean;
  quantitativo: boolean;
  minimo_itens?: number | null;
  maximo_itens?: number | null;
  ordem: number;
  ativo: boolean;
  adicionais: Adicional[];
  created_at: string;
  updated_at: string;
}
```

### Adicional/Item
```typescript
interface Adicional {
  id: number;
  nome: string;
  descricao?: string | null;
  preco: number; // Preço efetivo no contexto do complemento
  custo: number;
  ativo: boolean;
  ordem: number;
  created_at: string;
  updated_at: string;
}
```

---

## 🔄 Fluxos de Trabalho Completos

### Fluxo 1: Criar Produto Completo com Complementos

1. **Criar o produto**
   ```
   POST /api/catalogo/admin/produtos/
   ```

2. **Criar complementos (se não existirem)**
   ```
   POST /api/catalogo/admin/complementos
   ```

3. **Criar itens/adicionais (se não existirem)**
   ```
   POST /api/catalogo/admin/adicionais
   ```

4. **Vincular itens aos complementos**
   ```
   POST /api/catalogo/admin/complementos/{complemento_id}/itens/vincular
   ```

5. **Vincular complementos ao produto**
   ```
   POST /api/catalogo/admin/complementos/produto/{cod_barras}/vincular
   ```

---

### Fluxo 2: Criar Receita Completa com Ingredientes e Complementos

1. **Criar a receita**
   ```
   POST /api/catalogo/admin/receitas/
   ```

2. **Adicionar ingredientes**
   ```
   POST /api/catalogo/admin/receitas/ingredientes
   ```

3. **Criar/vincular complementos (seguir passos 2-4 do Fluxo 1)**

4. **Vincular complementos à receita**
   ```
   POST /api/catalogo/admin/complementos/receita/{receita_id}/vincular
   ```

---

### Fluxo 3: Criar Combo Completo com Itens e Complementos

1. **Criar o combo**
   ```
   POST /api/catalogo/admin/combos/
   ```

2. **Criar/vincular complementos (seguir passos 2-4 do Fluxo 1)**

3. **Vincular complementos ao combo**
   ```
   POST /api/catalogo/admin/complementos/combo/{combo_id}/vincular
   ```

---

### Fluxo 4: Adicionar Item ao Pedido com Complementos

1. **Buscar informações do produto/receita/combo**
   ```
   GET /api/catalogo/admin/produtos/{cod_barras}
   GET /api/catalogo/admin/receitas/{receita_id}
   GET /api/catalogo/admin/combos/{combo_id}
   ```

2. **Buscar complementos disponíveis**
   ```
   GET /api/catalogo/admin/complementos/produto/{cod_barras}
   GET /api/catalogo/admin/complementos/receita/{receita_id}
   GET /api/catalogo/admin/complementos/combo/{combo_id}
   ```

3. **Adicionar ao pedido com complementos selecionados**
   ```
   POST /api/pedidos/{tipo}/pedidos/{pedido_id}/adicionar-produto
   ```

---

## 💡 Exemplos Práticos

### Exemplo 1: Criar Hambúrguer com Complementos

```typescript
// 1. Criar produto
const produto = await criarProduto({
  cod_empresa: 1,
  descricao: 'Hambúrguer Artesanal',
  preco_venda: 25.90,
  custo: 10.50,
  imagem: imagemFile
});

// 2. Criar complemento "Tamanho"
const complementoTamanho = await criarComplemento({
  empresa_id: 1,
  nome: 'Tamanho',
  descricao: 'Escolha o tamanho',
  obrigatorio: true,
  quantitativo: false,
  minimo_itens: 1,
  maximo_itens: 1,
  ordem: 1
});

// 3. Criar itens do complemento
const itemPequeno = await criarAdicional({
  empresa_id: 1,
  nome: 'Pequeno',
  preco: 0,
  custo: 0
});

const itemGrande = await criarAdicional({
  empresa_id: 1,
  nome: 'Grande',
  preco: 5.00,
  custo: 2.00
});

// 4. Vincular itens ao complemento
await vincularItensComplemento(complementoTamanho.id, {
  item_ids: [itemPequeno.id, itemGrande.id],
  ordens: [0, 1]
});

// 5. Vincular complemento ao produto
await vincularComplementosProduto(produto.cod_barras, {
  complemento_ids: [complementoTamanho.id]
});
```

---

### Exemplo 2: Criar Pizza (Receita) com Ingredientes e Complementos

```typescript
// 1. Criar receita
const receita = await criarReceita({
  empresa_id: 1,
  nome: 'Pizza Margherita',
  descricao: 'Pizza tradicional italiana',
  preco_venda: 45.90,
  ativo: true,
  disponivel: true
});

// 2. Adicionar ingredientes
await adicionarIngrediente({
  receita_id: receita.id,
  ingrediente_id: 5, // Farinha
  quantidade: 500.0
});

await adicionarIngrediente({
  receita_id: receita.id,
  ingrediente_id: 8, // Queijo
  quantidade: 200.0
});

// 3. Criar e vincular complemento "Borda"
const complementoBorda = await criarComplemento({
  empresa_id: 1,
  nome: 'Borda',
  descricao: 'Escolha o tipo de borda',
  obrigatorio: false,
  quantitativo: false,
  minimo_itens: 0,
  maximo_itens: 1,
  ordem: 2
});

// ... criar itens e vincular (similar ao exemplo 1)

// 4. Vincular complemento à receita
await vincularComplementosReceita(receita.id, {
  complemento_ids: [complementoBorda.id]
});
```

---

### Exemplo 3: Adicionar Produto ao Pedido com Complementos

```typescript
// 1. Buscar produto e seus complementos
const produto = await buscarProduto('7891234567890');
const complementos = await listarComplementosProduto('7891234567890');

// 2. Usuário seleciona complementos no frontend
const complementosSelecionados = [
  {
    complemento_id: 1, // Tamanho
    adicionais: [
      {
        adicional_id: 10, // Grande
        quantidade: 1
      }
    ]
  },
  {
    complemento_id: 2, // Adicionais
    adicionais: [
      {
        adicional_id: 20, // Bacon
        quantidade: 2
      }
    ]
  }
];

// 3. Adicionar ao pedido
await adicionarProdutoPedido(pedidoId, {
  tipo: 'produto',
  identificador: '7891234567890',
  quantidade: 1,
  complementos: complementosSelecionados,
  observacao: 'Sem cebola'
});
```

---

## ⚠️ Validações e Regras Importantes

### Regras de Negócio

1. **Empresa:**
   - Todos os recursos (produtos, receitas, combos, complementos, itens) devem pertencer à mesma empresa
   - O backend valida automaticamente

2. **Vinculação de Complementos:**
   - Ao vincular complementos, **todas as vinculações anteriores são removidas**
   - Sempre inclua todos os IDs que deseja manter + os novos

3. **Vinculação de Itens:**
   - Ao vincular itens a um complemento, **todas as vinculações anteriores são removidas**
   - Sempre inclua todos os IDs que deseja manter + os novos

4. **Preços:**
   - Cada item tem um preço padrão
   - Um item pode ter preço diferente em cada complemento
   - Use `preco_complemento` ao vincular ou o endpoint específico de atualização

5. **Ordem:**
   - Complementos e itens têm ordem de exibição
   - A ordem pode ser atualizada independentemente

6. **Código de Barras:**
   - Se não fornecido ao criar produto, será gerado automaticamente
   - Deve ser único no sistema

---

## 📝 Checklist de Implementação

### Produtos
- [ ] Listar produtos com paginação e busca
- [ ] Criar produto com upload de imagem
- [ ] Atualizar produto (parcial)
- [ ] Deletar produto
- [ ] Vincular complementos a produtos

### Receitas
- [ ] Listar receitas com filtros
- [ ] Criar receita
- [ ] Atualizar receita
- [ ] Deletar receita
- [ ] Gerenciar ingredientes (adicionar, atualizar, remover)
- [ ] Vincular complementos a receitas

### Combos
- [ ] Listar combos com paginação e busca
- [ ] Criar combo com itens e upload de imagem
- [ ] Atualizar combo (parcial, incluindo itens)
- [ ] Deletar combo
- [ ] Vincular complementos a combos

### Complementos
- [ ] CRUD completo de complementos
- [ ] CRUD completo de itens/adicionais
- [ ] Vincular itens a complementos
- [ ] Gerenciar ordem de itens (arrastar e soltar)
- [ ] Atualizar preço específico por complemento

### Integração com Pedidos
- [ ] Buscar produtos/receitas/combos disponíveis
- [ ] Buscar complementos de cada item
- [ ] Adicionar item ao pedido com complementos selecionados
- [ ] Validar seleção de complementos (obrigatórios, limites)
- [ ] Calcular preço total com complementos

---

## 🔗 Endpoints Resumo

### Produtos
- `GET /api/catalogo/admin/produtos/` - Listar
- `POST /api/catalogo/admin/produtos/` - Criar
- `PUT /api/catalogo/admin/produtos/{cod_barras}` - Atualizar
- `DELETE /api/catalogo/admin/produtos/{cod_barras}` - Deletar

### Receitas
- `GET /api/catalogo/admin/receitas/` - Listar
- `POST /api/catalogo/admin/receitas/` - Criar
- `GET /api/catalogo/admin/receitas/{receita_id}` - Buscar
- `PUT /api/catalogo/admin/receitas/{receita_id}` - Atualizar
- `DELETE /api/catalogo/admin/receitas/{receita_id}` - Deletar
- `GET /api/catalogo/admin/receitas/{receita_id}/ingredientes` - Listar ingredientes
- `POST /api/catalogo/admin/receitas/ingredientes` - Adicionar ingrediente
- `PUT /api/catalogo/admin/receitas/ingredientes/{id}` - Atualizar ingrediente
- `DELETE /api/catalogo/admin/receitas/ingredientes/{id}` - Remover ingrediente

### Combos
- `GET /api/catalogo/admin/combos/` - Listar
- `POST /api/catalogo/admin/combos/` - Criar
- `GET /api/catalogo/admin/combos/{combo_id}` - Buscar
- `PUT /api/catalogo/admin/combos/{combo_id}` - Atualizar
- `DELETE /api/catalogo/admin/combos/{combo_id}` - Deletar

### Complementos
- `GET /api/catalogo/admin/complementos` - Listar
- `POST /api/catalogo/admin/complementos` - Criar
- `GET /api/catalogo/admin/complementos/{id}` - Buscar
- `PUT /api/catalogo/admin/complementos/{id}` - Atualizar
- `DELETE /api/catalogo/admin/complementos/{id}` - Deletar

### Itens/Adicionais
- `GET /api/catalogo/admin/adicionais` - Listar
- `POST /api/catalogo/admin/adicionais` - Criar
- `GET /api/catalogo/admin/adicionais/{id}` - Buscar
- `PUT /api/catalogo/admin/adicionais/{id}` - Atualizar
- `DELETE /api/catalogo/admin/adicionais/{id}` - Deletar

### Vinculações
- `POST /api/catalogo/admin/complementos/produto/{cod_barras}/vincular` - Vincular a produto
- `GET /api/catalogo/admin/complementos/produto/{cod_barras}` - Listar de produto
- `POST /api/catalogo/admin/complementos/receita/{receita_id}/vincular` - Vincular a receita
- `GET /api/catalogo/admin/complementos/receita/{receita_id}` - Listar de receita
- `POST /api/catalogo/admin/complementos/combo/{combo_id}/vincular` - Vincular a combo
- `GET /api/catalogo/admin/complementos/combo/{combo_id}` - Listar de combo
- `POST /api/catalogo/admin/complementos/{id}/itens/vincular` - Vincular itens
- `POST /api/catalogo/admin/complementos/{id}/itens/adicionar` - Adicionar item
- `GET /api/catalogo/admin/complementos/{id}/itens` - Listar itens
- `DELETE /api/catalogo/admin/complementos/{id}/itens/{item_id}` - Remover item
- `PUT /api/catalogo/admin/complementos/{id}/itens/ordem` - Atualizar ordem
- `PUT /api/catalogo/admin/complementos/{id}/itens/{item_id}/preco` - Atualizar preço

### Pedidos
- `POST /api/pedidos/{tipo}/pedidos/{pedido_id}/adicionar-produto` - Adicionar item ao pedido

---

## 📞 Suporte

Para mais detalhes técnicos, consulte:
- `docs/API_RECEITAS_CRUD.md` - Documentação detalhada de receitas
- `docs/API_COMBOS_CRUD.md` - Documentação detalhada de combos
- `docs/FRONTEND_COMPLEMENTOS_RECEITAS_COMBOS_ADMIN.md` - Documentação de complementos
- `docs/DOC_COMPLEMENTOS_RELACIONAMENTOS_CHECKOUT.md` - Documentação técnica de complementos

---

**Última atualização:** Janeiro 2024

