# Documentação da API de Receitas

## Visão Geral

A API de Receitas permite gerenciar ingredientes e adicionais de produtos. Ela é usada para criar receitas de produtos, definindo quais ingredientes são necessários para produzir um produto e quais adicionais podem ser adicionados a ele.

**Base URL:** `/api/mensura/admin/receitas`

**Autenticação:** Requer autenticação de administrador (token JWT no header `Authorization`)

---

## Endpoints de Ingredientes

### 1. Listar Ingredientes de um Produto

Retorna todos os ingredientes associados a um produto específico.

**Endpoint:** `GET /{cod_barras}/ingredientes`

**Parâmetros:**
- `cod_barras` (path, string, obrigatório): Código de barras do produto

**Resposta de Sucesso (200):**
```json
[
  {
    "id": 1,
    "produto_cod_barras": "7891234567890",
    "ingrediente_cod_barras": "7891234567891",
    "quantidade": 2.5,
    "unidade": "kg"
  },
  {
    "id": 2,
    "produto_cod_barras": "7891234567890",
    "ingrediente_cod_barras": "7891234567892",
    "quantidade": 500.0,
    "unidade": "ml"
  }
]
```

**Exemplo de Requisição:**
```javascript
const response = await fetch('/api/mensura/admin/receitas/7891234567890/ingredientes', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

const ingredientes = await response.json();
```

---

### 2. Adicionar Ingrediente a um Produto

Adiciona um novo ingrediente à receita de um produto.

**Endpoint:** `POST /ingredientes`

**Body (JSON):**
```json
{
  "produto_cod_barras": "7891234567890",
  "ingrediente_cod_barras": "7891234567891",
  "quantidade": 2.5,
  "unidade": "kg"
}
```

**Campos:**
- `produto_cod_barras` (string, obrigatório): Código de barras do produto
- `ingrediente_cod_barras` (string, obrigatório): Código de barras do ingrediente
- `quantidade` (float, opcional): Quantidade necessária do ingrediente
- `unidade` (string, opcional, max 10 caracteres): Unidade de medida (ex: "kg", "ml", "un")

**Resposta de Sucesso (201):**
```json
{
  "id": 1,
  "produto_cod_barras": "7891234567890",
  "ingrediente_cod_barras": "7891234567891",
  "quantidade": 2.5,
  "unidade": "kg"
}
```

**Erros Possíveis:**
- `400 Bad Request`: Produto ou ingrediente inválido, ou ingrediente já cadastrado
- `404 Not Found`: Produto ou ingrediente não encontrado

**Exemplo de Requisição:**
```javascript
const response = await fetch('/api/mensura/admin/receitas/ingredientes', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    produto_cod_barras: '7891234567890',
    ingrediente_cod_barras: '7891234567891',
    quantidade: 2.5,
    unidade: 'kg'
  })
});

const ingrediente = await response.json();
```

---

### 3. Atualizar Ingrediente

Atualiza a quantidade e/ou unidade de um ingrediente existente.

**Endpoint:** `PUT /ingredientes/{ingrediente_id}`

**Parâmetros:**
- `ingrediente_id` (path, integer, obrigatório): ID do ingrediente a ser atualizado

**Body (JSON):**
```json
{
  "quantidade": 3.0,
  "unidade": "kg"
}
```

**Campos:**
- `quantidade` (float, opcional): Nova quantidade
- `unidade` (string, opcional, max 10 caracteres): Nova unidade

**Resposta de Sucesso (200):**
```json
{
  "id": 1,
  "produto_cod_barras": "7891234567890",
  "ingrediente_cod_barras": "7891234567891",
  "quantidade": 3.0,
  "unidade": "kg"
}
```

**Erros Possíveis:**
- `404 Not Found`: Ingrediente não encontrado

**Exemplo de Requisição:**
```javascript
const response = await fetch('/api/mensura/admin/receitas/ingredientes/1', {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    quantidade: 3.0,
    unidade: 'kg'
  })
});

const ingredienteAtualizado = await response.json();
```

---

### 4. Remover Ingrediente

Remove um ingrediente da receita de um produto.

**Endpoint:** `DELETE /ingredientes/{ingrediente_id}`

**Parâmetros:**
- `ingrediente_id` (path, integer, obrigatório): ID do ingrediente a ser removido

**Resposta de Sucesso (204):**
Sem conteúdo no body

**Erros Possíveis:**
- `404 Not Found`: Ingrediente não encontrado

**Exemplo de Requisição:**
```javascript
const response = await fetch('/api/mensura/admin/receitas/ingredientes/1', {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

if (response.status === 204) {
  console.log('Ingrediente removido com sucesso');
}
```

---

## Endpoints de Adicionais

### 1. Listar Adicionais de um Produto

Retorna todos os adicionais disponíveis para um produto específico.

**Endpoint:** `GET /{cod_barras}/adicionais`

**Parâmetros:**
- `cod_barras` (path, string, obrigatório): Código de barras do produto

**Resposta de Sucesso (200):**
```json
[
  {
    "id": 1,
    "produto_cod_barras": "7891234567890",
    "adicional_cod_barras": "7891234567893",
    "preco": 5.50
  },
  {
    "id": 2,
    "produto_cod_barras": "7891234567890",
    "adicional_cod_barras": "7891234567894",
    "preco": 3.00
  }
]
```

**Exemplo de Requisição:**
```javascript
const response = await fetch('/api/mensura/admin/receitas/7891234567890/adicionais', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

const adicionais = await response.json();
```

---

### 2. Adicionar Adicional a um Produto

Adiciona um novo adicional disponível para um produto.

**Endpoint:** `POST /adicionais`

**Body (JSON):**
```json
{
  "produto_cod_barras": "7891234567890",
  "adicional_cod_barras": "7891234567893",
  "preco": 5.50
}
```

**Campos:**
- `produto_cod_barras` (string, obrigatório): Código de barras do produto
- `adicional_cod_barras` (string, obrigatório): Código de barras do adicional
- `preco` (decimal, opcional): Preço do adicional

**Resposta de Sucesso (201):**
```json
{
  "id": 1,
  "produto_cod_barras": "7891234567890",
  "adicional_cod_barras": "7891234567893",
  "preco": 5.50
}
```

**Erros Possíveis:**
- `400 Bad Request`: Produto ou adicional inválido, ou adicional já cadastrado
- `404 Not Found`: Produto ou adicional não encontrado

**Exemplo de Requisição:**
```javascript
const response = await fetch('/api/mensura/admin/receitas/adicionais', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    produto_cod_barras: '7891234567890',
    adicional_cod_barras: '7891234567893',
    preco: 5.50
  })
});

const adicional = await response.json();
```

---

### 3. Atualizar Adicional

Atualiza o preço de um adicional existente.

**Endpoint:** `PUT /adicionais/{adicional_id}`

**Parâmetros:**
- `adicional_id` (path, integer, obrigatório): ID do adicional a ser atualizado

**Body (JSON):**
```json
{
  "preco": 6.00
}
```

**Campos:**
- `preco` (float, opcional): Novo preço do adicional

**Resposta de Sucesso (200):**
```json
{
  "id": 1,
  "produto_cod_barras": "7891234567890",
  "adicional_cod_barras": "7891234567893",
  "preco": 6.00
}
```

**Erros Possíveis:**
- `404 Not Found`: Adicional não encontrado

**Exemplo de Requisição:**
```javascript
const response = await fetch('/api/mensura/admin/receitas/adicionais/1', {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    preco: 6.00
  })
});

const adicionalAtualizado = await response.json();
```

---

### 4. Remover Adicional

Remove um adicional de um produto.

**Endpoint:** `DELETE /adicionais/{adicional_id}`

**Parâmetros:**
- `adicional_id` (path, integer, obrigatório): ID do adicional a ser removido

**Resposta de Sucesso (204):**
Sem conteúdo no body

**Erros Possíveis:**
- `404 Not Found`: Adicional não encontrado

**Exemplo de Requisição:**
```javascript
const response = await fetch('/api/mensura/admin/receitas/adicionais/1', {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

if (response.status === 204) {
  console.log('Adicional removido com sucesso');
}
```

---

## Tipos de Dados (Schemas)

### IngredienteIn (Request)
```typescript
interface IngredienteIn {
  produto_cod_barras: string;        // obrigatório, min 1 caractere
  ingrediente_cod_barras: string;     // obrigatório, min 1 caractere
  quantidade?: number;                // opcional
  unidade?: string;                   // opcional, max 10 caracteres
}
```

### IngredienteOut (Response)
```typescript
interface IngredienteOut {
  id: number;
  produto_cod_barras: string;
  ingrediente_cod_barras: string;
  quantidade?: number;
  unidade?: string;
}
```

### AdicionalIn (Request)
```typescript
interface AdicionalIn {
  produto_cod_barras: string;        // obrigatório, min 1 caractere
  adicional_cod_barras: string;       // obrigatório, min 1 caractere
  preco?: number;                     // opcional (decimal)
}
```

### AdicionalOut (Response)
```typescript
interface AdicionalOut {
  id: number;
  produto_cod_barras: string;
  adicional_cod_barras: string;
  preco?: number;                     // decimal
}
```

---

## Códigos de Status HTTP

- `200 OK`: Requisição bem-sucedida (GET, PUT)
- `201 Created`: Recurso criado com sucesso (POST)
- `204 No Content`: Recurso removido com sucesso (DELETE)
- `400 Bad Request`: Dados inválidos ou recurso já existe
- `401 Unauthorized`: Token de autenticação inválido ou ausente
- `403 Forbidden`: Sem permissão para acessar o recurso
- `404 Not Found`: Recurso não encontrado
- `500 Internal Server Error`: Erro interno do servidor

---

## Exemplos de Uso Completo

### Exemplo 1: Gerenciar Receita Completa de um Produto

```javascript
// 1. Listar ingredientes atuais
const ingredientes = await fetch(
  `/api/mensura/admin/receitas/${codBarras}/ingredientes`,
  { headers: { 'Authorization': `Bearer ${token}` } }
).then(r => r.json());

// 2. Adicionar novo ingrediente
await fetch('/api/mensura/admin/receitas/ingredientes', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    produto_cod_barras: codBarras,
    ingrediente_cod_barras: '7891234567891',
    quantidade: 2.5,
    unidade: 'kg'
  })
});

// 3. Atualizar quantidade de um ingrediente
await fetch('/api/mensura/admin/receitas/ingredientes/1', {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    quantidade: 3.0,
    unidade: 'kg'
  })
});

// 4. Remover um ingrediente
await fetch('/api/mensura/admin/receitas/ingredientes/1', {
  method: 'DELETE',
  headers: { 'Authorization': `Bearer ${token}` }
});
```

### Exemplo 2: Gerenciar Adicionais de um Produto

```javascript
// 1. Listar adicionais atuais
const adicionais = await fetch(
  `/api/mensura/admin/receitas/${codBarras}/adicionais`,
  { headers: { 'Authorization': `Bearer ${token}` } }
).then(r => r.json());

// 2. Adicionar novo adicional
await fetch('/api/mensura/admin/receitas/adicionais', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    produto_cod_barras: codBarras,
    adicional_cod_barras: '7891234567893',
    preco: 5.50
  })
});

// 3. Atualizar preço de um adicional
await fetch('/api/mensura/admin/receitas/adicionais/1', {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    preco: 6.00
  })
});

// 4. Remover um adicional
await fetch('/api/mensura/admin/receitas/adicionais/1', {
  method: 'DELETE',
  headers: { 'Authorization': `Bearer ${token}` }
});
```

---

## Observações Importantes

1. **Validação de Produtos**: Tanto o produto quanto o ingrediente/adicional devem existir no cadastro de produtos antes de serem associados.

2. **Unicidade**: Não é possível adicionar o mesmo ingrediente ou adicional duas vezes ao mesmo produto. A API retornará erro 400 se tentar.

3. **Código de Barras**: Todos os produtos, ingredientes e adicionais são identificados por código de barras (string).

4. **Unidades de Medida**: Para ingredientes, a unidade é opcional e pode ser qualquer string de até 10 caracteres (ex: "kg", "ml", "un", "g", "l").

5. **Preços**: Os preços dos adicionais são opcionais e podem ser atualizados posteriormente.

6. **Autenticação**: Todos os endpoints requerem autenticação de administrador. Certifique-se de incluir o token JWT no header `Authorization` no formato `Bearer {token}`.

---

## Tratamento de Erros

### Exemplo de Tratamento de Erros em JavaScript

```javascript
async function adicionarIngrediente(dados) {
  try {
    const response = await fetch('/api/mensura/admin/receitas/ingredientes', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(dados)
    });

    if (!response.ok) {
      const error = await response.json();
      
      if (response.status === 400) {
        throw new Error(`Erro de validação: ${error.detail || error.message}`);
      } else if (response.status === 404) {
        throw new Error('Produto ou ingrediente não encontrado');
      } else if (response.status === 401) {
        throw new Error('Token de autenticação inválido');
      } else {
        throw new Error(`Erro ${response.status}: ${error.detail || error.message}`);
      }
    }

    return await response.json();
  } catch (error) {
    console.error('Erro ao adicionar ingrediente:', error);
    throw error;
  }
}
```

---

## Integração com React (Exemplo)

```typescript
import { useState, useEffect } from 'react';

interface Ingrediente {
  id: number;
  produto_cod_barras: string;
  ingrediente_cod_barras: string;
  quantidade?: number;
  unidade?: string;
}

export function useReceitas(codBarras: string) {
  const [ingredientes, setIngredientes] = useState<Ingrediente[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const token = localStorage.getItem('auth_token');

  useEffect(() => {
    async function carregarIngredientes() {
      try {
        setLoading(true);
        const response = await fetch(
          `/api/mensura/admin/receitas/${codBarras}/ingredientes`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          }
        );

        if (!response.ok) {
          throw new Error('Erro ao carregar ingredientes');
        }

        const data = await response.json();
        setIngredientes(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro desconhecido');
      } finally {
        setLoading(false);
      }
    }

    if (codBarras) {
      carregarIngredientes();
    }
  }, [codBarras, token]);

  const adicionarIngrediente = async (dados: Omit<Ingrediente, 'id'>) => {
    const response = await fetch('/api/mensura/admin/receitas/ingredientes', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(dados)
    });

    if (!response.ok) {
      throw new Error('Erro ao adicionar ingrediente');
    }

    const novoIngrediente = await response.json();
    setIngredientes([...ingredientes, novoIngrediente]);
    return novoIngrediente;
  };

  const removerIngrediente = async (id: number) => {
    const response = await fetch(
      `/api/mensura/admin/receitas/ingredientes/${id}`,
      {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) {
      throw new Error('Erro ao remover ingrediente');
    }

    setIngredientes(ingredientes.filter(ing => ing.id !== id));
  };

  return {
    ingredientes,
    loading,
    error,
    adicionarIngrediente,
    removerIngrediente
  };
}
```

---

**Última atualização:** 2024

