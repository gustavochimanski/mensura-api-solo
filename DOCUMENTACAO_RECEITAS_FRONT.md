# Documentação de API - Receitas

## Base URL
```
https://teste2.mensuraapi.com.br
```

## Autenticação
Todas as rotas requerem autenticação de admin via Bearer Token (JWT).

```
Authorization: Bearer {token}
```

---

## Endpoints Disponíveis

### 1. Listar Ingredientes de um Produto

**GET** `/api/cadastros/admin/receitas/{cod_barras}/ingredientes`

Lista todos os ingredientes de uma receita (produto).

#### Parâmetros de URL
- `cod_barras` (string, obrigatório): Código de barras do produto

#### Resposta (200 OK)
```json
[
  {
    "id": 1,
    "produto_cod_barras": "7891234567890",
    "ingrediente_cod_barras": "7899876543210",
    "quantidade": 2.5,
    "unidade": "kg"
  },
  {
    "id": 2,
    "produto_cod_barras": "7891234567890",
    "ingrediente_cod_barras": "7891112223334",
    "quantidade": 500.0,
    "unidade": "ml"
  }
]
```

#### Exemplo de Requisição
```javascript
const response = await fetch(
  `${BASE_URL}/api/cadastros/admin/receitas/7891234567890/ingredientes`,
  {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  }
);
const ingredientes = await response.json();
```

---

### 2. Adicionar Ingrediente a uma Receita

**POST** `/api/cadastros/admin/receitas/ingredientes`

Adiciona um ingrediente a uma receita (produto).

#### Body (JSON)
```json
{
  "produto_cod_barras": "7891234567890",
  "ingrediente_cod_barras": "7899876543210",
  "quantidade": 2.5,
  "unidade": "kg"
}
```

#### Campos
- `produto_cod_barras` (string, obrigatório): Código de barras do produto que terá a receita
- `ingrediente_cod_barras` (string, obrigatório): Código de barras do ingrediente
- `quantidade` (float, opcional): Quantidade do ingrediente
- `unidade` (string, opcional, max 10 chars): Unidade de medida (ex: "kg", "ml", "un")

#### Resposta (201 Created)
```json
{
  "id": 1,
  "produto_cod_barras": "7891234567890",
  "ingrediente_cod_barras": "7899876543210",
  "quantidade": 2.5,
  "unidade": "kg"
}
```

#### Exemplo de Requisição
```javascript
const response = await fetch(
  `${BASE_URL}/api/cadastros/admin/receitas/ingredientes`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      produto_cod_barras: "7891234567890",
      ingrediente_cod_barras: "7899876543210",
      quantidade: 2.5,
      unidade: "kg"
    })
  }
);
const ingrediente = await response.json();
```

---

### 3. Atualizar Ingrediente

**PUT** `/api/cadastros/admin/receitas/ingredientes/{ingrediente_id}`

Atualiza a quantidade e/ou unidade de um ingrediente.

#### Parâmetros de URL
- `ingrediente_id` (integer, obrigatório): ID do ingrediente

#### Body (JSON)
```json
{
  "quantidade": 3.0,
  "unidade": "kg"
}
```

#### Campos
- `quantidade` (float, opcional): Nova quantidade
- `unidade` (string, opcional): Nova unidade

#### Resposta (200 OK)
```json
{
  "id": 1,
  "produto_cod_barras": "7891234567890",
  "ingrediente_cod_barras": "7899876543210",
  "quantidade": 3.0,
  "unidade": "kg"
}
```

#### Exemplo de Requisição
```javascript
const response = await fetch(
  `${BASE_URL}/api/cadastros/admin/receitas/ingredientes/1`,
  {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      quantidade: 3.0,
      unidade: "kg"
    })
  }
);
const ingrediente = await response.json();
```

---

### 4. Remover Ingrediente

**DELETE** `/api/cadastros/admin/receitas/ingredientes/{ingrediente_id}`

Remove um ingrediente de uma receita.

#### Parâmetros de URL
- `ingrediente_id` (integer, obrigatório): ID do ingrediente

#### Resposta (204 No Content)
Sem corpo de resposta.

#### Exemplo de Requisição
```javascript
const response = await fetch(
  `${BASE_URL}/api/cadastros/admin/receitas/ingredientes/1`,
  {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);
// response.status === 204
```

---

### 5. Listar Adicionais de um Produto

**GET** `/api/cadastros/admin/receitas/{cod_barras}/adicionais`

Lista todos os adicionais disponíveis para um produto.

#### Parâmetros de URL
- `cod_barras` (string, obrigatório): Código de barras do produto

#### Resposta (200 OK)
```json
[
  {
    "id": 1,
    "produto_cod_barras": "7891234567890",
    "adicional_cod_barras": "7895556667778",
    "preco": 5.50
  },
  {
    "id": 2,
    "produto_cod_barras": "7891234567890",
    "adicional_cod_barras": "7899998887776",
    "preco": 3.00
  }
]
```

#### Exemplo de Requisição
```javascript
const response = await fetch(
  `${BASE_URL}/api/cadastros/admin/receitas/7891234567890/adicionais`,
  {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  }
);
const adicionais = await response.json();
```

---

### 6. Adicionar Adicional a um Produto

**POST** `/api/cadastros/admin/receitas/adicionais`

Adiciona um adicional disponível para um produto.

#### Body (JSON)
```json
{
  "produto_cod_barras": "7891234567890",
  "adicional_cod_barras": "7895556667778",
  "preco": 5.50
}
```

#### Campos
- `produto_cod_barras` (string, obrigatório): Código de barras do produto
- `adicional_cod_barras` (string, obrigatório): Código de barras do adicional
- `preco` (decimal, opcional): Preço do adicional

#### Resposta (201 Created)
```json
{
  "id": 1,
  "produto_cod_barras": "7891234567890",
  "adicional_cod_barras": "7895556667778",
  "preco": 5.50
}
```

#### Exemplo de Requisição
```javascript
const response = await fetch(
  `${BASE_URL}/api/cadastros/admin/receitas/adicionais`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      produto_cod_barras: "7891234567890",
      adicional_cod_barras: "7895556667778",
      preco: 5.50
    })
  }
);
const adicional = await response.json();
```

---

### 7. Atualizar Adicional

**PUT** `/api/cadastros/admin/receitas/adicionais/{adicional_id}`

Atualiza o preço de um adicional.

#### Parâmetros de URL
- `adicional_id` (integer, obrigatório): ID do adicional

#### Body (JSON)
```json
{
  "preco": 6.00
}
```

#### Campos
- `preco` (float, opcional): Novo preço

#### Resposta (200 OK)
```json
{
  "id": 1,
  "produto_cod_barras": "7891234567890",
  "adicional_cod_barras": "7895556667778",
  "preco": 6.00
}
```

#### Exemplo de Requisição
```javascript
const response = await fetch(
  `${BASE_URL}/api/cadastros/admin/receitas/adicionais/1`,
  {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      preco: 6.00
    })
  }
);
const adicional = await response.json();
```

---

### 8. Remover Adicional

**DELETE** `/api/cadastros/admin/receitas/adicionais/{adicional_id}`

Remove um adicional de um produto.

#### Parâmetros de URL
- `adicional_id` (integer, obrigatório): ID do adicional

#### Resposta (204 No Content)
Sem corpo de resposta.

#### Exemplo de Requisição
```javascript
const response = await fetch(
  `${BASE_URL}/api/cadastros/admin/receitas/adicionais/1`,
  {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);
// response.status === 204
```

---

## Modelos de Dados

### IngredienteOut
```typescript
interface IngredienteOut {
  id: number;
  produto_cod_barras: string;
  ingrediente_cod_barras: string;
  quantidade: number | null;
  unidade: string | null;
}
```

### IngredienteIn
```typescript
interface IngredienteIn {
  produto_cod_barras: string;  // obrigatório, min 1 char
  ingrediente_cod_barras: string;  // obrigatório, min 1 char
  quantidade?: number | null;
  unidade?: string | null;  // max 10 chars
}
```

### AdicionalOut
```typescript
interface AdicionalOut {
  id: number;
  produto_cod_barras: string;
  adicional_cod_barras: string;
  preco: number | null;
}
```

### AdicionalIn
```typescript
interface AdicionalIn {
  produto_cod_barras: string;  // obrigatório, min 1 char
  adicional_cod_barras: string;  // obrigatório, min 1 char
  preco?: number | null;
}
```

---

## Códigos de Status HTTP

- `200 OK`: Requisição bem-sucedida
- `201 Created`: Recurso criado com sucesso
- `204 No Content`: Recurso removido com sucesso (sem corpo)
- `400 Bad Request`: Dados inválidos
- `401 Unauthorized`: Token ausente ou inválido
- `404 Not Found`: Recurso não encontrado
- `500 Internal Server Error`: Erro no servidor

---

## Exemplo de Uso Completo (React/TypeScript)

```typescript
// types.ts
export interface Ingrediente {
  id: number;
  produto_cod_barras: string;
  ingrediente_cod_barras: string;
  quantidade: number | null;
  unidade: string | null;
}

export interface Adicional {
  id: number;
  produto_cod_barras: string;
  adicional_cod_barras: string;
  preco: number | null;
}

// api.ts
const BASE_URL = 'https://teste2.mensuraapi.com.br';

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// Receitas API
export const receitasAPI = {
  // Ingredientes
  listarIngredientes: (codBarras: string): Promise<Ingrediente[]> =>
    apiRequest<Ingrediente[]>(`/api/cadastros/admin/receitas/${codBarras}/ingredientes`),

  adicionarIngrediente: (data: {
    produto_cod_barras: string;
    ingrediente_cod_barras: string;
    quantidade?: number;
    unidade?: string;
  }): Promise<Ingrediente> =>
    apiRequest<Ingrediente>('/api/cadastros/admin/receitas/ingredientes', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  atualizarIngrediente: (
    id: number,
    data: { quantidade?: number; unidade?: string }
  ): Promise<Ingrediente> =>
    apiRequest<Ingrediente>(`/api/cadastros/admin/receitas/ingredientes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  removerIngrediente: (id: number): Promise<void> =>
    apiRequest<void>(`/api/cadastros/admin/receitas/ingredientes/${id}`, {
      method: 'DELETE',
    }),

  // Adicionais
  listarAdicionais: (codBarras: string): Promise<Adicional[]> =>
    apiRequest<Adicional[]>(`/api/cadastros/admin/receitas/${codBarras}/adicionais`),

  adicionarAdicional: (data: {
    produto_cod_barras: string;
    adicional_cod_barras: string;
    preco?: number;
  }): Promise<Adicional> =>
    apiRequest<Adicional>('/api/cadastros/admin/receitas/adicionais', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  atualizarAdicional: (
    id: number,
    data: { preco?: number }
  ): Promise<Adicional> =>
    apiRequest<Adicional>(`/api/cadastros/admin/receitas/adicionais/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  removerAdicional: (id: number): Promise<void> =>
    apiRequest<void>(`/api/cadastros/admin/receitas/adicionais/${id}`, {
      method: 'DELETE',
    }),
};

// Componente de exemplo
function ReceitasComponent({ codBarras }: { codBarras: string }) {
  const [ingredientes, setIngredientes] = useState<Ingrediente[]>([]);
  const [adicionais, setAdicionais] = useState<Adicional[]>([]);

  useEffect(() => {
    async function carregar() {
      try {
        const [ing, add] = await Promise.all([
          receitasAPI.listarIngredientes(codBarras),
          receitasAPI.listarAdicionais(codBarras),
        ]);
        setIngredientes(ing);
        setAdicionais(add);
      } catch (error) {
        console.error('Erro ao carregar receitas:', error);
      }
    }
    carregar();
  }, [codBarras]);

  const handleAdicionarIngrediente = async () => {
    try {
      const novo = await receitasAPI.adicionarIngrediente({
        produto_cod_barras: codBarras,
        ingrediente_cod_barras: '7899876543210',
        quantidade: 2.5,
        unidade: 'kg',
      });
      setIngredientes([...ingredientes, novo]);
    } catch (error) {
      console.error('Erro ao adicionar ingrediente:', error);
    }
  };

  return (
    <div>
      <h2>Ingredientes</h2>
      {ingredientes.map((ing) => (
        <div key={ing.id}>
          {ing.ingrediente_cod_barras} - {ing.quantidade} {ing.unidade}
        </div>
      ))}
      
      <h2>Adicionais</h2>
      {adicionais.map((add) => (
        <div key={add.id}>
          {add.adicional_cod_barras} - R$ {add.preco}
        </div>
      ))}
    </div>
  );
}
```

---

## Notas Importantes

1. **Autenticação**: Todas as rotas requerem token JWT válido no header `Authorization`
2. **Código de Barras**: O `cod_barras` é usado como identificador do produto
3. **Ingredientes vs Adicionais**: 
   - **Ingredientes**: Componentes da receita (com quantidade e unidade)
   - **Adicionais**: Opções extras para o produto (com preço)
4. **Campos Opcionais**: `quantidade`, `unidade` e `preco` podem ser `null`
5. **Unidade**: Máximo de 10 caracteres para a unidade de medida

