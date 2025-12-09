# 📚 Documentação Admin - API de Adicionais e Complementos

## 🎯 Visão Geral

Esta documentação descreve todos os endpoints **administrativos** para gerenciar:
- ✅ **Adicionais** - Itens independentes que podem ser usados em complementos, receitas, combos
- ✅ **Complementos** - Grupos de adicionais com configurações
- ✅ **Vínculos** - Relacionamento N:N entre complementos e adicionais

**Autenticação**: Requer token JWT de admin (via `Authorization: Bearer {token}`)

---

## 🔧 Endpoints - Adicionais

**Base URL**: `/api/catalogo/admin/adicionais`

### 1. Criar Adicional

```http
POST /api/catalogo/admin/adicionais/
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "empresa_id": 1,
  "nome": "Ketchup",
  "descricao": "Molho de tomate",
  "preco": 0.0,
  "custo": 0.0,
  "ativo": true
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "nome": "Ketchup",
  "descricao": "Molho de tomate",
  "preco": 0.0,
  "custo": 0.0,
  "ativo": true,
  "ordem": 0,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### 2. Listar Adicionais

```http
GET /api/catalogo/admin/adicionais/?empresa_id=1&apenas_ativos=true
Authorization: Bearer {token}
```

**Query Parameters:**
- `empresa_id` (required): ID da empresa
- `apenas_ativos` (optional): `true` ou `false` (default: `true`)
- `termo` (optional): Termo de busca (busca em nome ou descrição)

**Response:** `200 OK` (List[AdicionalResponse])

**Exemplo com busca:**
```http
GET /api/catalogo/admin/adicionais/?empresa_id=1&termo=ketchup&apenas_ativos=true
Authorization: Bearer {token}
```

Retorna adicionais cujo nome ou descrição contenham "ketchup" (case-insensitive).

### 3. Buscar Adicional

```http
GET /api/catalogo/admin/adicionais/{adicional_id}
Authorization: Bearer {token}
```

**Response:** `200 OK` (AdicionalResponse)

### 4. Atualizar Adicional

```http
PUT /api/catalogo/admin/adicionais/{adicional_id}
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "nome": "Ketchup Premium",
  "preco": 1.50,
  "ativo": false
}
```

**Response:** `200 OK` (AdicionalResponse)

### 5. Deletar Adicional

```http
DELETE /api/catalogo/admin/adicionais/{adicional_id}
Authorization: Bearer {token}
```

**Response:** `200 OK`
```json
{
  "message": "Adicional deletado com sucesso"
}
```

⚠️ **Atenção**: Deletar um adicional remove automaticamente:
- Vínculos com complementos (via CASCADE)
- Vínculos com receitas (via RESTRICT - pode dar erro se houver)
- Vínculos com combos (se houver)

---

## 🔧 Endpoints - Complementos

**Base URL**: `/api/catalogo/admin/complementos`

### 1. Criar Complemento

```http
POST /api/catalogo/admin/complementos/
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "empresa_id": 1,
  "nome": "Molhos",
  "descricao": "Escolha seus molhos",
  "obrigatorio": false,
  "quantitativo": false,
  "permite_multipla_escolha": true,
  "ordem": 0
}
```

**Response:** `201 Created` (ComplementoResponse)

### 2. Listar Complementos

```http
GET /api/catalogo/admin/complementos/?empresa_id=1&apenas_ativos=true
Authorization: Bearer {token}
```

**Query Parameters:**
- `empresa_id` (required): ID da empresa
- `apenas_ativos` (optional): `true` ou `false` (default: `true`)

**Response:** `200 OK` (List[ComplementoResponse])

### 3. Buscar Complemento

```http
GET /api/catalogo/admin/complementos/{complemento_id}
Authorization: Bearer {token}
```

**Response:** `200 OK` (ComplementoResponse)

### 4. Atualizar Complemento

```http
PUT /api/catalogo/admin/complementos/{complemento_id}
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "nome": "Molhos Premium",
  "obrigatorio": true,
  "ativo": false
}
```

**Response:** `200 OK` (ComplementoResponse)

### 5. Deletar Complemento

```http
DELETE /api/catalogo/admin/complementos/{complemento_id}
Authorization: Bearer {token}
```

**Response:** `200 OK`
```json
{
  "message": "Complemento deletado com sucesso"
}
```

⚠️ **Atenção**: Deletar um complemento remove apenas os vínculos, **não deleta** os adicionais.

---

## 🔗 Endpoints - Vínculos

### 1. Vincular Adicionais a um Complemento

```http
POST /api/catalogo/admin/complementos/{complemento_id}/itens/vincular
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "item_ids": [1, 2, 3],
  "ordens": [0, 1, 2]
}
```

**Response:** `200 OK`
```json
{
  "complemento_id": 1,
  "itens_vinculados": 3,
  "message": "Itens vinculados com sucesso"
}
```

### 2. Desvincular Adicional de um Complemento

```http
DELETE /api/catalogo/admin/complementos/{complemento_id}/itens/{item_id}
Authorization: Bearer {token}
```

**Response:** `200 OK`
```json
{
  "message": "Item desvinculado com sucesso"
}
```

### 3. Listar Adicionais de um Complemento

```http
GET /api/catalogo/admin/complementos/{complemento_id}/itens?apenas_ativos=true
Authorization: Bearer {token}
```

**Response:** `200 OK` (List[AdicionalResponse])

### 4. Atualizar Ordem dos Adicionais

```http
PUT /api/catalogo/admin/complementos/{complemento_id}/itens/ordem
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "item_id": 1,
  "nova_ordem": 2
}
```

**Response:** `200 OK`
```json
{
  "message": "Ordem dos itens atualizada com sucesso"
}
```

---

## 🔗 Endpoints - Vínculos com Produtos

### 1. Vincular Complementos a um Produto

```http
POST /api/catalogo/admin/complementos/produto/{cod_barras}/vincular
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "complemento_ids": [1, 2, 3]
}
```

**Response:** `200 OK`
```json
{
  "cod_barras": "7891234567890",
  "complementos_vinculados": 3,
  "message": "Complementos vinculados com sucesso"
}
```

### 2. Listar Complementos de um Produto

```http
GET /api/catalogo/admin/complementos/produto/{cod_barras}?apenas_ativos=true
Authorization: Bearer {token}
```

**Response:** `200 OK` (List[ComplementoResponse])

---

## 📊 Schemas

### CriarItemRequest
```typescript
interface CriarItemRequest {
  empresa_id: number;
  nome: string;                    // 1-100 caracteres
  descricao?: string;              // Máx 255 caracteres
  preco: number;                   // Decimal (18,2) - Default: 0
  custo: number;                   // Decimal (18,2) - Default: 0
  ativo?: boolean;                // Default: true
}
```

### AtualizarAdicionalRequest
```typescript
interface AtualizarAdicionalRequest {
  nome?: string;
  descricao?: string;
  preco?: number;
  custo?: number;
  ativo?: boolean;
}
```

### AdicionalResponse
```typescript
interface AdicionalResponse {
  id: number;                      // ID do adicional (usado como adicional_id nos pedidos)
  nome: string;
  descricao?: string;
  preco: number;
  custo: number;
  ativo: boolean;
  ordem: number;                   // Ordem quando vinculado a um complemento
  created_at: string;              // ISO 8601
  updated_at: string;              // ISO 8601
}
```

### CriarComplementoRequest
```typescript
interface CriarComplementoRequest {
  empresa_id: number;
  nome: string;                    // 1-100 caracteres
  descricao?: string;              // Máx 255 caracteres
  obrigatorio: boolean;            // Default: false
  quantitativo: boolean;           // Default: false
  permite_multipla_escolha: boolean; // Default: true
  ordem: number;                   // Default: 0
}
```

### AtualizarComplementoRequest
```typescript
interface AtualizarComplementoRequest {
  nome?: string;
  descricao?: string;
  obrigatorio?: boolean;
  quantitativo?: boolean;
  permite_multipla_escolha?: boolean;
  ativo?: boolean;
  ordem?: number;
}
```

### ComplementoResponse
```typescript
interface ComplementoResponse {
  id: number;
  empresa_id: number;
  nome: string;
  descricao?: string;
  obrigatorio: boolean;
  quantitativo: boolean;
  permite_multipla_escolha: boolean;
  ordem: number;
  ativo: boolean;
  adicionais: AdicionalResponse[];  // Lista de adicionais vinculados
  created_at: string;               // ISO 8601
  updated_at: string;                // ISO 8601
}
```

### VincularItensComplementoRequest
```typescript
interface VincularItensComplementoRequest {
  item_ids: number[];              // IDs dos adicionais
  ordens?: number[];               // Ordem de cada item (opcional)
}
```

### VincularComplementosProdutoRequest
```typescript
interface VincularComplementosProdutoRequest {
  complemento_ids: number[];        // IDs dos complementos
}
```

---

## 💡 Exemplos de Uso

### Exemplo 1: Criar Estrutura Completa

```typescript
// 1. Criar adicionais
const ketchup = await fetch('/api/catalogo/admin/adicionais/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    empresa_id: 1,
    nome: "Ketchup",
    preco: 0.0
  })
});
const ketchupData = await ketchup.json();

const maionese = await fetch('/api/catalogo/admin/adicionais/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    empresa_id: 1,
    nome: "Maionese",
    preco: 0.0
  })
});
const maioneseData = await maionese.json();

// 2. Criar complemento
const molhos = await fetch('/api/catalogo/admin/complementos/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    empresa_id: 1,
    nome: "Molhos",
    obrigatorio: false,
    permite_multipla_escolha: true
  })
});
const molhosData = await molhos.json();

// 3. Vincular adicionais ao complemento
await fetch(`/api/catalogo/admin/complementos/${molhosData.id}/itens/vincular`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    item_ids: [ketchupData.id, maioneseData.id],
    ordens: [0, 1]
  })
});

// 4. Vincular complemento a um produto
await fetch(`/api/catalogo/admin/complementos/produto/7891234567890/vincular`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    complemento_ids: [molhosData.id]
  })
});
```

### Exemplo 2: Buscar Adicionais

```typescript
// Buscar adicionais por termo
const adicionais = await fetch(
  '/api/catalogo/admin/adicionais/?empresa_id=1&termo=ketchup&apenas_ativos=true',
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

const adicionaisData = await adicionais.json();
// Retorna adicionais cujo nome ou descrição contenham "ketchup"
```

### Exemplo 3: Reutilizar Adicional em Múltiplos Complementos

```typescript
// Criar adicional "Ketchup"
const ketchup = await criarAdicional({ nome: "Ketchup", preco: 0.0 });

// Criar complemento "Molhos"
const molhos = await criarComplemento({ nome: "Molhos" });

// Criar complemento "Extras"
const extras = await criarComplemento({ nome: "Extras" });

// Vincular "Ketchup" a ambos (reutilização!)
await vincularItens(molhos.id, [ketchup.id]);
await vincularItens(extras.id, [ketchup.id]); // Mesmo adicional!
```

---

## 📝 Tabela de Endpoints

### Adicionais
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/catalogo/admin/adicionais/` | Criar adicional |
| GET | `/api/catalogo/admin/adicionais/` | Listar/Buscar adicionais (com `termo` para busca) |
| GET | `/api/catalogo/admin/adicionais/{id}` | Buscar adicional por ID |
| PUT | `/api/catalogo/admin/adicionais/{id}` | Atualizar adicional |
| DELETE | `/api/catalogo/admin/adicionais/{id}` | Deletar adicional |

### Complementos
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/catalogo/admin/complementos/` | Criar complemento |
| GET | `/api/catalogo/admin/complementos/` | Listar complementos |
| GET | `/api/catalogo/admin/complementos/{id}` | Buscar complemento |
| PUT | `/api/catalogo/admin/complementos/{id}` | Atualizar complemento |
| DELETE | `/api/catalogo/admin/complementos/{id}` | Deletar complemento |

### Vínculos
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/catalogo/admin/complementos/{id}/itens/vincular` | Vincular adicionais |
| DELETE | `/api/catalogo/admin/complementos/{id}/itens/{item_id}` | Desvincular adicional |
| GET | `/api/catalogo/admin/complementos/{id}/itens` | Listar adicionais |
| PUT | `/api/catalogo/admin/complementos/{id}/itens/ordem` | Atualizar ordem |

### Produtos
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/catalogo/admin/complementos/produto/{cod_barras}/vincular` | Vincular complementos |
| GET | `/api/catalogo/admin/complementos/produto/{cod_barras}` | Listar complementos |

---

## 🔍 Códigos de Status HTTP

- `200 OK`: Sucesso
- `201 Created`: Criado com sucesso
- `400 Bad Request`: Dados inválidos
- `401 Unauthorized`: Não autenticado
- `403 Forbidden`: Sem permissão
- `404 Not Found`: Recurso não encontrado
- `422 Unprocessable Entity`: Erro de validação

---

## ⚠️ Regras de Negócio

1. **Adicionais são independentes**: Podem existir sem estar em nenhum complemento
2. **Reutilização**: Um adicional pode estar em vários complementos (N:N)
3. **Deleção**: 
   - Deletar adicional remove de todos os complementos (CASCADE)
   - Deletar complemento não deleta os adicionais
4. **Ordem**: Específica por complemento (mesmo adicional pode ter ordens diferentes)
5. **Empresa**: Adicionais e complementos devem pertencer à mesma empresa

---

**Documentação Client**: `docs/API_ADICIONAIS_CLIENT.md`

