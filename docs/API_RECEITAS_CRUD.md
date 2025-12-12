# 📘 API CRUD Completo: Receitas

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Autenticação](#autenticação)
3. [Endpoints de Receitas](#endpoints-de-receitas)
4. [Endpoints de Ingredientes](#endpoints-de-ingredientes)
5. [Endpoints de Adicionais](#endpoints-de-adicionais)
6. [Endpoints de Complementos](#endpoints-de-complementos)
7. [Schemas e Tipos](#schemas-e-tipos)
8. [Exemplos de Uso](#exemplos-de-uso)
9. [Códigos de Erro](#códigos-de-erro)

---

## 🎯 Visão Geral

A API de Receitas permite gerenciar receitas, seus ingredientes, adicionais e complementos. Uma receita é um produto composto que pode ter:

- **Ingredientes**: Matérias-primas que compõem a receita (relacionamento N:N)
- **Adicionais**: Produtos adicionais que podem ser vendidos junto com a receita (DEPRECADO - usar complementos)
- **Complementos**: Grupos de adicionais organizados hierarquicamente (NOVO - preferencial)

**Base URL:** `/api/catalogo/admin/receitas`

---

## 🔐 Autenticação

Todos os endpoints requerem autenticação via Bearer Token:

```
Authorization: Bearer {access_token}
```

O token é obtido através do endpoint de login admin.

---

## 📦 Endpoints de Receitas

### 1. Criar Receita

**POST** `/api/catalogo/admin/receitas/`

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

**Response:** `201 Created`
```json
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
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

**Campos:**
- `empresa_id` (obrigatório): ID da empresa
- `nome` (obrigatório): Nome da receita (1-100 caracteres)
- `descricao` (opcional): Descrição da receita
- `preco_venda` (obrigatório): Preço de venda (Decimal)
- `imagem` (opcional): URL da imagem
- `ativo` (opcional, default: true): Se a receita está ativa
- `disponivel` (opcional, default: true): Se a receita está disponível para venda

**Nota:** O campo `custo_total` é calculado automaticamente com base nos ingredientes vinculados.

---

### 2. Listar Receitas

**GET** `/api/catalogo/admin/receitas/`

**Query Parameters:**
- `empresa_id` (opcional): Filtrar por empresa
- `ativo` (opcional): Filtrar por status ativo (true/false)
- `search` (opcional): Busca textual em nome/descrição (case-insensitive)

**Exemplos:**
```
GET /api/catalogo/admin/receitas/?empresa_id=1
GET /api/catalogo/admin/receitas/?empresa_id=1&ativo=true
GET /api/catalogo/admin/receitas/?search=pizza
GET /api/catalogo/admin/receitas/?empresa_id=1&ativo=true&search=margherita
```

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
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  }
]
```

---

### 3. Listar Receitas com Ingredientes

**GET** `/api/catalogo/admin/receitas/com-ingredientes`

**Query Parameters:** (mesmos do endpoint anterior)

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
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00",
    "ingredientes": [
      {
        "id": 1,
        "receita_id": 1,
        "ingrediente_id": 5,
        "quantidade": 500.0,
        "ingrediente_nome": "Farinha de Trigo",
        "ingrediente_descricao": "Farinha especial para pizza",
        "ingrediente_unidade_medida": "g",
        "ingrediente_custo": 0.05
      }
    ]
  }
]
```

---

### 4. Buscar Receita por ID

**GET** `/api/catalogo/admin/receitas/{receita_id}`

**Path Parameters:**
- `receita_id` (obrigatório): ID da receita

**Response:** `200 OK`
```json
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
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

**Erros:**
- `404 Not Found`: Receita não encontrada

---

### 5. Atualizar Receita

**PUT** `/api/catalogo/admin/receitas/{receita_id}`

**Path Parameters:**
- `receita_id` (obrigatório): ID da receita

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

**Response:** `200 OK`
```json
{
  "id": 1,
  "empresa_id": 1,
  "nome": "Pizza Margherita Especial",
  "descricao": "Pizza tradicional italiana com ingredientes premium",
  "preco_venda": 49.90,
  "custo_total": 15.50,
  "imagem": "https://exemplo.com/pizza-premium.jpg",
  "ativo": true,
  "disponivel": true,
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T11:45:00"
}
```

**Nota:** Apenas os campos enviados serão atualizados. O `custo_total` é recalculado automaticamente.

---

### 6. Deletar Receita

**DELETE** `/api/catalogo/admin/receitas/{receita_id}`

**Path Parameters:**
- `receita_id` (obrigatório): ID da receita

**Response:** `204 No Content`

**Erros:**
- `404 Not Found`: Receita não encontrada

**Nota:** Ao deletar uma receita, os ingredientes e adicionais vinculados são removidos automaticamente (cascade).

---

## 🥘 Endpoints de Ingredientes

### 1. Listar Ingredientes de uma Receita

**GET** `/api/catalogo/admin/receitas/{receita_id}/ingredientes`

**Path Parameters:**
- `receita_id` (obrigatório): ID da receita

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "receita_id": 1,
    "ingrediente_id": 5,
    "quantidade": 500.0
  },
  {
    "id": 2,
    "receita_id": 1,
    "ingrediente_id": 8,
    "quantidade": 200.0
  }
]
```

---

### 2. Adicionar Ingrediente a uma Receita

**POST** `/api/catalogo/admin/receitas/ingredientes`

**Request Body:**
```json
{
  "receita_id": 1,
  "ingrediente_id": 5,
  "quantidade": 500.0
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "receita_id": 1,
  "ingrediente_id": 5,
  "quantidade": 500.0
}
```

**Erros:**
- `400 Bad Request`: Ingrediente já cadastrado nesta receita (duplicata)
- `404 Not Found`: Receita ou ingrediente não encontrado

**Nota:** Um ingrediente pode estar vinculado a VÁRIAS receitas (relacionamento N:N). Mas não pode estar duplicado na mesma receita.

---

### 3. Atualizar Quantidade de Ingrediente

**PUT** `/api/catalogo/admin/receitas/ingredientes/{receita_ingrediente_id}`

**Path Parameters:**
- `receita_ingrediente_id` (obrigatório): ID do vínculo ingrediente-receita

**Request Body:**
```json
{
  "quantidade": 600.0
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "receita_id": 1,
  "ingrediente_id": 5,
  "quantidade": 600.0
}
```

**Nota:** O `receita_ingrediente_id` é o ID da tabela de relacionamento, não o ID do ingrediente.

---

### 4. Remover Ingrediente de uma Receita

**DELETE** `/api/catalogo/admin/receitas/ingredientes/{receita_ingrediente_id}`

**Path Parameters:**
- `receita_ingrediente_id` (obrigatório): ID do vínculo ingrediente-receita

**Response:** `204 No Content`

**Nota:** Remove apenas o vínculo, não deleta o ingrediente do sistema.

---

## 🍕 Endpoints de Adicionais

> ⚠️ **DEPRECADO**: Adicionais diretos estão sendo substituídos por **Complementos**. Use complementos para novas implementações.

### 1. Listar Adicionais de uma Receita

**GET** `/api/catalogo/admin/receitas/{receita_id}/adicionais`

**Path Parameters:**
- `receita_id` (obrigatório): ID da receita

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "receita_id": 1,
    "adicional_id": 10,
    "preco": 5.00
  }
]
```

---

### 2. Adicionar Adicional a uma Receita

**POST** `/api/catalogo/admin/receitas/adicionais`

**Request Body:**
```json
{
  "receita_id": 1,
  "adicional_id": 10
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "receita_id": 1,
  "adicional_id": 10,
  "preco": 5.00
}
```

**Nota:** O preço é sincronizado automaticamente com o cadastro do adicional.

---

### 3. Atualizar Adicional de uma Receita

**PUT** `/api/catalogo/admin/receitas/adicionais/{adicional_id}`

**Path Parameters:**
- `adicional_id` (obrigatório): ID do adicional

**Response:** `200 OK`
```json
{
  "id": 1,
  "receita_id": 1,
  "adicional_id": 10,
  "preco": 6.00
}
```

**Nota:** Sincroniza o preço com o cadastro atual do produto (sempre busca do ProdutoEmpModel).

---

### 4. Remover Adicional de uma Receita

**DELETE** `/api/catalogo/admin/receitas/adicionais/{adicional_id}`

**Path Parameters:**
- `adicional_id` (obrigatório): ID do adicional

**Response:** `204 No Content`

---

## 🎁 Endpoints de Complementos

> ✅ **NOVO**: Complementos são a forma preferencial de gerenciar adicionais em receitas.

### 1. Vincular Complementos a uma Receita

**PUT** `/api/catalogo/admin/receitas/{receita_id}/complementos`

**Path Parameters:**
- `receita_id` (obrigatório): ID da receita

**Request Body:**
```json
{
  "complemento_ids": [1, 2, 3]
}
```

**Response:** `200 OK`
```json
{
  "receita_id": 1,
  "complementos_vinculados": [
    {
      "id": 1,
      "nome": "Tamanho",
      "obrigatorio": false,
      "quantitativo": false,
      "permite_multipla_escolha": false,
      "minimo_itens": null,
      "maximo_itens": null,
      "ordem": 0
    },
    {
      "id": 2,
      "nome": "Bebida",
      "obrigatorio": true,
      "quantitativo": false,
      "permite_multipla_escolha": false,
      "minimo_itens": 1,
      "maximo_itens": 1,
      "ordem": 1
    }
  ],
  "message": "Complementos vinculados com sucesso"
}
```

**Nota:** 
- Remove todas as vinculações existentes e cria novas
- A ordem dos complementos é definida pela ordem no array
- Para mais detalhes sobre complementos, consulte `docs/API_COMBOS_CRUD.md`

---

### 2. Listar Complementos de uma Receita (Admin)

**GET** `/api/catalogo/admin/complementos/receita/{receita_id}`

**Path Parameters:**
- `receita_id` (obrigatório): ID da receita

**Query Parameters:**
- `apenas_ativos` (opcional, default: true): Filtrar apenas complementos ativos

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "empresa_id": 1,
    "nome": "Tamanho",
    "descricao": "Escolha o tamanho da pizza",
    "obrigatorio": false,
    "quantitativo": false,
    "permite_multipla_escolha": false,
    "minimo_itens": null,
    "maximo_itens": null,
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
        "created_at": "2024-01-15T10:30:00",
        "updated_at": "2024-01-15T10:30:00"
      }
    ],
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  }
]
```

**Nota:** Este endpoint está no router de complementos, não no router de receitas.

---

## 📋 Schemas e Tipos

### ReceitaIn (Criar)
```typescript
interface ReceitaIn {
  empresa_id: number;
  nome: string;                    // 1-100 caracteres
  descricao?: string | null;
  preco_venda: number;              // Decimal
  imagem?: string | null;
  ativo?: boolean;                  // default: true
  disponivel?: boolean;             // default: true
}
```

### ReceitaOut (Response)
```typescript
interface ReceitaOut {
  id: number;
  empresa_id: number;
  nome: string;
  descricao?: string | null;
  preco_venda: number;              // Decimal
  custo_total: number;              // Decimal (calculado automaticamente)
  imagem?: string | null;
  ativo: boolean;
  disponivel: boolean;
  created_at: string;                // ISO 8601
  updated_at: string;                // ISO 8601
}
```

### ReceitaUpdate (Atualizar)
```typescript
interface ReceitaUpdate {
  nome?: string;                    // 1-100 caracteres
  descricao?: string | null;
  preco_venda?: number;             // Decimal
  imagem?: string | null;
  ativo?: boolean;
  disponivel?: boolean;
}
```

### ReceitaIngredienteIn
```typescript
interface ReceitaIngredienteIn {
  receita_id: number;
  ingrediente_id: number;
  quantidade?: number | null;       // float
}
```

### ReceitaIngredienteOut
```typescript
interface ReceitaIngredienteOut {
  id: number;                        // ID do vínculo
  receita_id: number;
  ingrediente_id: number;
  quantidade?: number | null;
}
```

### ReceitaComIngredientesOut
```typescript
interface ReceitaComIngredientesOut {
  id: number;
  empresa_id: number;
  nome: string;
  descricao?: string | null;
  preco_venda: number;
  custo_total: number;
  imagem?: string | null;
  ativo: boolean;
  disponivel: boolean;
  created_at: string;
  updated_at: string;
  ingredientes: ReceitaIngredienteDetalhadoOut[];
}
```

### ReceitaIngredienteDetalhadoOut
```typescript
interface ReceitaIngredienteDetalhadoOut {
  id: number;
  receita_id: number;
  ingrediente_id: number;
  quantidade?: number | null;
  ingrediente_nome?: string | null;
  ingrediente_descricao?: string | null;
  ingrediente_unidade_medida?: string | null;
  ingrediente_custo?: number | null;  // Decimal
}
```

### AdicionalIn
```typescript
interface AdicionalIn {
  receita_id: number;
  adicional_id: number;
}
```

### AdicionalOut
```typescript
interface AdicionalOut {
  id: number;
  receita_id: number;
  adicional_id: number;
  preco?: number | null;             // Decimal
}
```

### VincularComplementosReceitaRequest
```typescript
interface VincularComplementosReceitaRequest {
  complemento_ids: number[];
}
```

### VincularComplementosReceitaResponse
```typescript
interface VincularComplementosReceitaResponse {
  receita_id: number;
  complementos_vinculados: ComplementoResumidoResponse[];
  message: string;
}
```

---

## 💻 Exemplos de Uso

### Exemplo 1: Criar Receita Completa

```typescript
// 1. Criar receita
const receita = await fetch('/api/catalogo/admin/receitas/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    empresa_id: 1,
    nome: 'Pizza Margherita',
    descricao: 'Pizza tradicional italiana',
    preco_venda: 45.90,
    ativo: true,
    disponivel: true,
  }),
});

const receitaData = await receita.json();
const receitaId = receitaData.id;

// 2. Adicionar ingredientes
await Promise.all([
  fetch('/api/catalogo/admin/receitas/ingredientes', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      receita_id: receitaId,
      ingrediente_id: 5,
      quantidade: 500.0,
    }),
  }),
  fetch('/api/catalogo/admin/receitas/ingredientes', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      receita_id: receitaId,
      ingrediente_id: 8,
      quantidade: 200.0,
    }),
  }),
]);

// 3. Vincular complementos
await fetch(`/api/catalogo/admin/receitas/${receitaId}/complementos`, {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    complemento_ids: [1, 2, 3],
  }),
});
```

### Exemplo 2: Listar Receitas com Filtros

```typescript
// Listar receitas ativas de uma empresa
const receitas = await fetch(
  '/api/catalogo/admin/receitas/?empresa_id=1&ativo=true',
  {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  }
);

// Buscar receitas por nome
const receitasBusca = await fetch(
  '/api/catalogo/admin/receitas/?search=pizza',
  {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  }
);
```

### Exemplo 3: Atualizar Receita

```typescript
// Atualizar apenas o preço
await fetch(`/api/catalogo/admin/receitas/${receitaId}`, {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    preco_venda: 49.90,
  }),
});
```

### Exemplo 4: Gerenciar Ingredientes

```typescript
// Adicionar ingrediente (ignorar duplicatas)
const resultados = await Promise.allSettled(
  ingredientes.map(ing => 
    fetch('/api/catalogo/admin/receitas/ingredientes', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        receita_id: receitaId,
        ingrediente_id: ing.ingrediente_id,
        quantidade: ing.quantidade,
      }),
    })
  )
);

// Filtrar apenas erros que não são duplicatas
resultados.forEach((result, index) => {
  if (result.status === 'rejected') {
    console.error(`Erro ao adicionar ingrediente ${index}:`, result.reason);
  }
});
```

---

## ⚠️ Códigos de Erro

### 400 Bad Request
- Ingrediente já cadastrado nesta receita (duplicata)
- Dados inválidos no request body

### 401 Unauthorized
- Token ausente ou inválido
- Token expirado

### 403 Forbidden
- Usuário não tem permissão para acessar o recurso

### 404 Not Found
- Receita não encontrada
- Ingrediente não encontrado
- Adicional não encontrado
- Complemento não encontrado

### 500 Internal Server Error
- Erro interno do servidor

---

## 📝 Notas Importantes

1. **Custo Total**: O campo `custo_total` é calculado automaticamente com base nos ingredientes vinculados. Não é possível definir manualmente.

2. **Ingredientes Duplicados**: Um ingrediente não pode estar duplicado na mesma receita, mas pode estar em várias receitas diferentes.

3. **Complementos vs Adicionais**: 
   - **Adicionais** (DEPRECADO): Adicionais diretos na receita
   - **Complementos** (NOVO): Grupos hierárquicos de adicionais (preferencial)

4. **Ordem de Rotas**: Rotas sem parâmetros de path devem vir ANTES das rotas com parâmetros para evitar conflitos (ex: `/adicionais` vs `/{receita_id}/adicionais`).

5. **Cascade Delete**: Ao deletar uma receita, todos os ingredientes e adicionais vinculados são removidos automaticamente.

---

## 🔗 Endpoints Relacionados

- **Ingredientes**: `docs/API_INGREDIENTES_CRUD.md`
- **Complementos**: `docs/API_COMBOS_CRUD.md` (seção de complementos)
- **Produtos**: `docs/API_PRODUTOS_CRUD.md`

---

**Última atualização:** Dezembro 2024

