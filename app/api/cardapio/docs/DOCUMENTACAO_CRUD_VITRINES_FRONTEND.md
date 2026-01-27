# Documentação Completa - CRUD de Vitrines (Frontend)

Esta documentação descreve **todos os endpoints CRUD** para manipulação de vitrines do sistema.

---

## 📋 Índice

1. [Base URL e Autenticação](#base-url-e-autenticação)
2. [Estrutura de Dados](#estrutura-de-dados)
3. [Endpoints CRUD](#endpoints-crud)
4. [Validações e Regras de Negócio](#validações-e-regras-de-negócio)
5. [Códigos de Status HTTP](#códigos-de-status-http)
6. [Exemplos Práticos](#exemplos-práticos)
7. [Tratamento de Erros](#tratamento-de-erros)

---

## 🔐 Base URL e Autenticação

### Base URL

**Prefixo Admin**: `/api/cardapio/admin/vitrines`

**Exemplos:**
- **Local**: `http://localhost:8000/api/cardapio/admin/vitrines`
- **Produção**: `https://seu-dominio.com/api/cardapio/admin/vitrines`

### Autenticação

**Todos os endpoints**: Requerem autenticação de **administrador** via `get_current_user` (token JWT no header `Authorization: Bearer <token>`)

**Headers obrigatórios:**
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**⚠️ Importante**: Apenas usuários autenticados como administrador podem acessar estes endpoints.

---

## 📊 Estrutura de Dados

### Parâmetro `landingpage_true` (Query)

Todos os endpoints do CRUD admin de vitrines aceitam o parâmetro **query**:

- `landingpage_true` (boolean, default: `false`)
  - **false** (padrão): opera nas vitrines tradicionais (`cardapio.vitrines_dv`) e permite vínculo com categoria (`cod_categoria`).
  - **true**: opera nas vitrines da landing page store (`cardapio.vitrines_landingpage_store`) e **não permite** vínculo com categoria.

> Regra: quando `landingpage_true=true`, **não envie `cod_categoria`** (o backend retorna 400).

### CriarVitrineRequest (Criar Vitrine)

```typescript
interface CriarVitrineRequest {
  cod_categoria?: number;        // Opcional - ID da categoria vinculada
  titulo: string;                 // Obrigatório - Título da vitrine (1-100 caracteres)
  is_home?: boolean;              // Opcional - Se deve aparecer na home (default: false)
}
```

**⚠️ Importante**: O campo `ordem` **não é mais aceito** no payload de criação. A ordem é calculada automaticamente como a próxima ordem disponível (MAX(ordem) + 1).

### AtualizarVitrineRequest (Atualizar Vitrine)

```typescript
interface AtualizarVitrineRequest {
  cod_categoria?: number;        // Opcional - ID da categoria vinculada
  titulo?: string;                // Opcional - Novo título (1-100 caracteres)
  ordem?: number;                // Opcional - Nova ordem de exibição
  is_home?: boolean;             // Opcional - Se deve aparecer na home
}
```

**⚠️ Importante**: O campo `ordem` **só pode ser definido no update**, não na criação.

### VitrineOut (Resposta)

```typescript
interface VitrineOut {
  id: number;                    // ID único da vitrine
  cod_categoria?: number;        // ID da categoria vinculada (se houver)
  titulo: string;                // Título da vitrine
  slug: string;                  // Slug único da vitrine (gerado automaticamente)
  ordem: number;                 // Ordem de exibição
  is_home: boolean;              // Se aparece na home
}
```

---

## 🚀 Endpoints CRUD

### 1. Criar Vitrine (CREATE)

Cria uma nova vitrine no sistema. A ordem é calculada automaticamente.

**Endpoint:**
```
POST /api/cardapio/admin/vitrines
```

**Headers:**
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**Body Request:**
```json
{
  "cod_categoria": 5,
  "titulo": "Promoções do Dia",
  "is_home": true
}
```

**Criar vitrine para Landing Page Store (sem categoria):**
```
POST /api/cardapio/admin/vitrines?landingpage_true=true
```

```json
{
  "titulo": "Vitrine Landing",
  "is_home": true
}
```

**Exemplo - Sem categoria:**
```json
{
  "titulo": "Vitrine Geral",
  "is_home": false
}
```

**Response (201 Created):**
```json
{
  "id": 15,
  "cod_categoria": 5,
  "titulo": "Promoções do Dia",
  "slug": "promocoes-do-dia",
  "ordem": 8,
  "is_home": true
}
```

**Validações:**
- `titulo` é obrigatório e deve ter entre 1 e 100 caracteres
- `cod_categoria` deve existir no banco de dados (se fornecido)
- O slug é gerado automaticamente a partir do título
- A ordem é calculada automaticamente (próxima ordem disponível)

**Erros Possíveis:**
- `400 Bad Request`: "Categoria inválida"
- `400 Bad Request`: "Conflito de dados ao criar vitrine"
- `401 Unauthorized`: Token ausente ou inválido
- `403 Forbidden`: Usuário não é administrador

---

### 2. Buscar Vitrines (SEARCH)

Busca vitrines com filtros opcionais.

**Endpoint:**
```
GET /api/cardapio/admin/vitrines/search
```

**Query Parameters:**
- `q` (string, opcional): Busca por título ou slug
- `cod_categoria` (integer, opcional): Filtra por categoria vinculada
- `is_home` (boolean, opcional): Filtra por vitrines da home
- `limit` (integer, opcional): Limite de resultados (default: 30, min: 1, max: 100)
- `offset` (integer, opcional): Offset para paginação (default: 0, min: 0)

**Exemplo:**
```
GET /api/cardapio/admin/vitrines/search?q=promo&is_home=true&limit=10
```

**Exemplo (Landing Page Store):**
```
GET /api/cardapio/admin/vitrines/search?landingpage_true=true&q=promo&limit=10
```

**Response (200 OK):**
```json
[
  {
    "id": 15,
    "cod_categoria": 5,
    "titulo": "Promoções do Dia",
    "slug": "promocoes-do-dia",
    "ordem": 8,
    "is_home": true
  },
  {
    "id": 16,
    "cod_categoria": 3,
    "titulo": "Promoções Especiais",
    "slug": "promocoes-especiais",
    "ordem": 9,
    "is_home": true
  }
]
```

---

### 3. Atualizar Vitrine (UPDATE)

Atualiza informações de uma vitrine existente. **Este é o único momento onde a ordem pode ser definida.**

**Endpoint:**
```
PUT /api/cardapio/admin/vitrines/{vitrine_id}
```

**Atualizar vitrine (Landing Page Store):**
```
PUT /api/cardapio/admin/vitrines/{vitrine_id}?landingpage_true=true&empresa_id=1
```

**Path Parameters:**
- `vitrine_id` (integer, obrigatório): ID da vitrine

**Body Request:**
```json
{
  "cod_categoria": 7,
  "titulo": "Promoções Atualizadas",
  "ordem": 3,
  "is_home": false
}
```

**Observações:**
- Todos os campos são **opcionais** (atualização parcial)
- O campo `ordem` **só pode ser definido no update**, não na criação
- Se `titulo` for alterado, o slug será regenerado automaticamente
- Se `cod_categoria` for fornecido, substituirá a categoria atual
- Para remover a categoria, envie `cod_categoria: null`

**Exemplo - Atualizar apenas ordem:**
```json
{
  "ordem": 1
}
```

**Exemplo - Atualizar apenas título:**
```json
{
  "titulo": "Novo Título da Vitrine"
}
```

**Exemplo - Atualizar apenas is_home:**
```json
{
  "is_home": true
}
```

**Exemplo - Atualizar múltiplos campos:**
```json
{
  "titulo": "Vitrine Premium",
  "ordem": 2,
  "is_home": true,
  "cod_categoria": 10
}
```

**Response (200 OK):**
```json
{
  "id": 15,
  "cod_categoria": 7,
  "titulo": "Promoções Atualizadas",
  "slug": "promocoes-atualizadas",
  "ordem": 3,
  "is_home": false
}
```

**Validações:**
- A vitrine deve existir
- Se `cod_categoria` for fornecido, deve existir no banco de dados
- Se `titulo` for fornecido, deve ter entre 1 e 100 caracteres
- Se `ordem` for fornecido, deve ser um número inteiro positivo

**Erros Possíveis:**
- `400 Bad Request`: "Categoria inválida"
- `400 Bad Request`: "Conflito de dados ao atualizar vitrine"
- `404 Not Found`: "Vitrine não encontrada"
- `401 Unauthorized`: Token ausente ou inválido
- `403 Forbidden`: Usuário não é administrador

---

### 4. Deletar Vitrine (DELETE)

Remove uma vitrine do sistema.

**Endpoint:**
```
DELETE /api/cardapio/admin/vitrines/{vitrine_id}
```

**Deletar vitrine (Landing Page Store):**
```
DELETE /api/cardapio/admin/vitrines/{vitrine_id}?landingpage_true=true&empresa_id=1
```

**Path Parameters:**
- `vitrine_id` (integer, obrigatório): ID da vitrine

**Exemplo:**
```
DELETE /api/cardapio/admin/vitrines/15
```

**Response (204 No Content):**
```
(sem corpo de resposta)
```

**⚠️ Atenção**: Esta operação é **irreversível**. A vitrine será removida permanentemente do banco de dados.

**Validações:**
- A vitrine deve existir
- A vitrine não pode ter produtos vinculados

**Erros Possíveis:**
- `400 Bad Request`: "Não é possível excluir. Existem produtos vinculados."
- `404 Not Found`: "Vitrine não encontrada"
- `401 Unauthorized`: Token ausente ou inválido
- `403 Forbidden`: Usuário não é administrador

---

### 5. Toggle Home (PATCH)

Define se a vitrine deve aparecer na home.

**Endpoint:**
```
PATCH /api/cardapio/admin/vitrines/{vitrine_id}/home
```

**Path Parameters:**
- `vitrine_id` (integer, obrigatório): ID da vitrine

**Body Request:**
```json
{
  "is_home": true
}
```

**Response (200 OK):**
```json
{
  "id": 15,
  "cod_categoria": 5,
  "titulo": "Promoções do Dia",
  "slug": "promocoes-do-dia",
  "ordem": 8,
  "is_home": true
}
```

---

## 🔒 Validações e Regras de Negócio

### Validações Gerais

1. **Título Único**: O slug gerado a partir do título deve ser único (gerado automaticamente)
2. **Categoria**: Se `cod_categoria` for fornecido, deve existir no banco de dados
3. **Ordem**: 
   - **Na criação**: Calculada automaticamente (não aceita no payload)
   - **No update**: Pode ser definida manualmente
4. **Produtos Vinculados**: Não é possível deletar uma vitrine que tenha produtos vinculados

### Regras de Negócio

1. **Criação de Vitrine:**
   - O sistema calcula automaticamente a próxima ordem disponível (MAX(ordem) + 1)
   - O slug é gerado automaticamente a partir do título
   - Se o slug já existir, será adicionado um sufixo numérico (ex: `vitrine-2`)
   - Valida se a categoria existe (se fornecida)

2. **Atualização de Vitrine:**
   - A ordem **só pode ser definida no update**
   - Todos os campos são opcionais (atualização parcial)
   - Se o título for alterado, o slug será regenerado
   - A categoria pode ser alterada ou removida

3. **Exclusão de Vitrine:**
   - Só é permitida se não houver produtos vinculados
   - Remove automaticamente todos os vínculos com categorias

---

## 📝 Códigos de Status HTTP

| Código | Significado | Quando Ocorre |
|--------|-------------|---------------|
| `200` | OK | Operação bem-sucedida (GET, PUT, PATCH) |
| `201` | Created | Vitrine criada com sucesso (POST) |
| `204` | No Content | Vitrine deletada com sucesso (DELETE) |
| `400` | Bad Request | Dados inválidos ou conflito |
| `401` | Unauthorized | Token ausente ou inválido |
| `403` | Forbidden | Usuário não é administrador |
| `404` | Not Found | Vitrine ou categoria não encontrada |

---

## 💡 Exemplos Práticos

### Exemplo 1: Criar uma vitrine simples

```typescript
const criarVitrine = async () => {
  const response = await fetch('http://localhost:8000/api/cardapio/admin/vitrines', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer seu_token_aqui',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      titulo: 'Lançamentos',
      is_home: true
    })
  });
  
  const vitrine = await response.json();
  console.log('Vitrine criada:', vitrine);
  // A ordem será calculada automaticamente
};
```

### Exemplo 2: Atualizar a ordem de uma vitrine

```typescript
const atualizarOrdem = async (vitrineId: number, novaOrdem: number) => {
  const response = await fetch(`http://localhost:8000/api/cardapio/admin/vitrines/${vitrineId}`, {
    method: 'PUT',
    headers: {
      'Authorization': 'Bearer seu_token_aqui',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      ordem: novaOrdem
    })
  });
  
  const vitrine = await response.json();
  console.log('Ordem atualizada:', vitrine);
};
```

### Exemplo 3: Buscar vitrines da home

```typescript
const buscarVitrinesHome = async () => {
  const response = await fetch(
    'http://localhost:8000/api/cardapio/admin/vitrines/search?is_home=true',
    {
      headers: {
        'Authorization': 'Bearer seu_token_aqui'
      }
    }
  );
  
  const vitrines = await response.json();
  console.log('Vitrines da home:', vitrines);
};
```

### Exemplo 4: Atualizar múltiplos campos

```typescript
const atualizarVitrine = async (vitrineId: number) => {
  const response = await fetch(`http://localhost:8000/api/cardapio/admin/vitrines/${vitrineId}`, {
    method: 'PUT',
    headers: {
      'Authorization': 'Bearer seu_token_aqui',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      titulo: 'Promoções de Verão',
      ordem: 1,
      is_home: true,
      cod_categoria: 5
    })
  });
  
  const vitrine = await response.json();
  console.log('Vitrine atualizada:', vitrine);
};
```

---

## ⚠️ Tratamento de Erros

### Estrutura de Erro Padrão

```json
{
  "detail": "Mensagem de erro descritiva"
}
```

### Exemplos de Erros

**Erro 400 - Categoria inválida:**
```json
{
  "detail": "Categoria inválida"
}
```

**Erro 404 - Vitrine não encontrada:**
```json
{
  "detail": "Vitrine não encontrada"
}
```

**Erro 400 - Produtos vinculados:**
```json
{
  "detail": "Não é possível excluir. Existem produtos vinculados."
}
```

### Tratamento no Frontend

```typescript
try {
  const response = await fetch(url, options);
  
  if (!response.ok) {
    const error = await response.json();
    
    switch (response.status) {
      case 400:
        console.error('Erro de validação:', error.detail);
        break;
      case 401:
        console.error('Não autenticado');
        // Redirecionar para login
        break;
      case 403:
        console.error('Sem permissão');
        break;
      case 404:
        console.error('Vitrine não encontrada:', error.detail);
        break;
      default:
        console.error('Erro desconhecido:', error.detail);
    }
  } else {
    const data = await response.json();
    return data;
  }
} catch (error) {
  console.error('Erro de rede:', error);
}
```

---

## 📌 Resumo das Mudanças

### ⚠️ Mudança Importante: Campo `ordem`

**Antes:**
- O campo `ordem` podia ser enviado no payload de criação
- Exemplo: `{ "titulo": "Vitrine", "ordem": 5 }`

**Agora:**
- O campo `ordem` **não é mais aceito** no payload de criação
- A ordem é calculada automaticamente como a próxima ordem disponível
- O campo `ordem` **só pode ser definido no update**
- Exemplo de criação: `{ "titulo": "Vitrine" }` (ordem calculada automaticamente)
- Exemplo de update: `{ "ordem": 5 }` (ordem pode ser definida)

---

## 🔗 Endpoints Relacionados

### Vínculos de Produtos

- `POST /api/cardapio/admin/vitrines/{vitrine_id}/vincular` - Vincular produto
- `DELETE /api/cardapio/admin/vitrines/{vitrine_id}/vincular/{cod_barras}` - Desvincular produto

### Vínculos de Combos

- `POST /api/cardapio/admin/vitrines/{vitrine_id}/vincular-combo` - Vincular combo
- `DELETE /api/cardapio/admin/vitrines/{vitrine_id}/vincular-combo/{combo_id}` - Desvincular combo

### Vínculos de Receitas

- `POST /api/cardapio/admin/vitrines/{vitrine_id}/vincular-receita` - Vincular receita
- `DELETE /api/cardapio/admin/vitrines/{vitrine_id}/vincular-receita/{receita_id}` - Desvincular receita

---

**Última atualização**: Janeiro 2026
