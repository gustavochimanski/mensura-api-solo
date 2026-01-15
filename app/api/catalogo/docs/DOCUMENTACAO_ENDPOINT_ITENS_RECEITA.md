# Documentação: Endpoint de Itens de Receita

## Endpoint

**GET** `/api/catalogo/admin/receitas/itens`

Lista todos os itens de uma receita, com suporte a filtro por tipo.

## Autenticação

Requer autenticação de administrador. Inclua o token no header:

```
Authorization: Bearer <seu_token>
```

## Query Parameters

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `receita_id` | integer | Sim | ID da receita |
| `tipo` | string | Não | Filtro por tipo de item. Valores válidos: `sub-receita`, `produto`, `combo` |

## Tipos de Itens

- **`sub-receita`**: Outras receitas usadas como item
- **`produto`**: Produtos normais do catálogo
- **`combo`**: Combos cadastrados

## Exemplos de Uso

### 1. Listar Todos os Itens

```http
GET /api/catalogo/admin/receitas/itens?receita_id=1
Authorization: Bearer <seu_token>
```

**Resposta (200):**
```json
[
  {
    "id": 10,
    "receita_id": 1,
    "receita_ingrediente_id": null,
    "produto_cod_barras": "PROD001",
    "combo_id": null,
    "quantidade": 2.0
  },
  {
    "id": 11,
    "receita_id": 1,
    "receita_ingrediente_id": 3,
    "produto_cod_barras": null,
    "combo_id": null,
    "quantidade": 1.5
  },
  {
    "id": 12,
    "receita_id": 1,
    "receita_ingrediente_id": null,
    "produto_cod_barras": "PROD002",
    "combo_id": null,
    "quantidade": 3.0
  },
  {
    "id": 13,
    "receita_id": 1,
    "receita_ingrediente_id": null,
    "produto_cod_barras": null,
    "combo_id": 2,
    "quantidade": 1.0
  }
]
```

### 2. Filtrar Apenas Sub-receitas

```http
GET /api/catalogo/admin/receitas/itens?receita_id=1&tipo=sub-receita
Authorization: Bearer <seu_token>
```

**Resposta (200):**
```json
[
  {
    "id": 11,
    "receita_id": 1,
    "receita_ingrediente_id": 3,
    "produto_cod_barras": null,
    "combo_id": null,
    "quantidade": 1.5
  }
]
```

### 3. Filtrar Apenas Produtos

```http
GET /api/catalogo/admin/receitas/itens?receita_id=1&tipo=produto
Authorization: Bearer <seu_token>
```

### 4. Filtrar Apenas Combos

```http
GET /api/catalogo/admin/receitas/itens?receita_id=1&tipo=combo
Authorization: Bearer <seu_token>
```

## Como Identificar o Tipo de Item

Para identificar o tipo de item na resposta, verifique qual campo não é `null`:

- **Sub-receita**: `receita_ingrediente_id` não é `null`
- **Produto**: `produto_cod_barras` não é `null`
- **Combo**: `combo_id` não é `null`

## Exemplos de Código

### TypeScript/JavaScript

```typescript
// Listar todos os itens
async function listarItensReceita(receitaId: number) {
  const token = localStorage.getItem('auth_token');
  
  const response = await fetch(
    `/api/catalogo/admin/receitas/itens?receita_id=${receitaId}`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      }
    }
  );
  
  if (!response.ok) {
    throw new Error('Erro ao listar itens da receita');
  }
  
  return await response.json();
}

// Filtrar por tipo
async function listarItensPorTipo(receitaId: number, tipo: 'sub-receita' | 'produto' | 'combo') {
  const token = localStorage.getItem('auth_token');
  
  const response = await fetch(
    `/api/catalogo/admin/receitas/itens?receita_id=${receitaId}&tipo=${tipo}`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      }
    }
  );
  
  if (!response.ok) {
    throw new Error('Erro ao listar itens da receita');
  }
  
  return await response.json();
}

// Exemplo de uso
const todosItens = await listarItensReceita(1);
const apenasSubReceitas = await listarItensPorTipo(1, 'sub-receita');
```

### React Hook

```typescript
import { useState, useEffect } from 'react';

interface ItemReceita {
  id: number;
  receita_id: number;
  ingrediente_id: number | null;
  receita_ingrediente_id: number | null;
  produto_cod_barras: string | null;
  combo_id: number | null;
  quantidade: number | null;
}

function useItensReceita(receitaId: number, tipo?: string) {
  const [itens, setItens] = useState<ItemReceita[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchItens() {
      try {
        setLoading(true);
        const token = localStorage.getItem('auth_token');
        const url = tipo 
          ? `/api/catalogo/admin/receitas/itens?receita_id=${receitaId}&tipo=${tipo}`
          : `/api/catalogo/admin/receitas/itens?receita_id=${receitaId}`;
        
        const response = await fetch(url, {
          headers: {
            'Authorization': `Bearer ${token}`,
          }
        });
        
        if (!response.ok) {
          throw new Error('Erro ao carregar itens');
        }
        
        const data = await response.json();
        setItens(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro desconhecido');
      } finally {
        setLoading(false);
      }
    }

    if (receitaId) {
      fetchItens();
    }
  }, [receitaId, tipo]);

  return { itens, loading, error };
}

// Uso no componente
function ReceitaItens({ receitaId }: { receitaId: number }) {
  const [tipoFiltro, setTipoFiltro] = useState<string>('');
  const { itens, loading, error } = useItensReceita(receitaId, tipoFiltro || undefined);

  if (loading) return <div>Carregando...</div>;
  if (error) return <div>Erro: {error}</div>;

  return (
    <div>
      <select value={tipoFiltro} onChange={(e) => setTipoFiltro(e.target.value)}>
        <option value="">Todos os tipos</option>
        <option value="ingrediente">Ingredientes</option>
        <option value="sub-receita">Sub-receitas</option>
        <option value="produto">Produtos</option>
        <option value="combo">Combos</option>
      </select>

      <ul>
        {itens.map(item => (
          <li key={item.id}>
            {item.ingrediente_id && <span>🧂 Ingrediente ID: {item.ingrediente_id}</span>}
            {item.receita_ingrediente_id && <span>📋 Sub-receita ID: {item.receita_ingrediente_id}</span>}
            {item.produto_cod_barras && <span>📦 Produto: {item.produto_cod_barras}</span>}
            {item.combo_id && <span>🎁 Combo ID: {item.combo_id}</span>}
            <span> - Quantidade: {item.quantidade}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Axios

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: '/api/catalogo/admin',
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
  }
});

// Listar todos os itens
async function listarItensReceita(receitaId: number) {
  const response = await api.get('/receitas/itens', {
    params: { receita_id: receitaId }
  });
  return response.data;
}

// Filtrar por tipo
async function listarItensPorTipo(
  receitaId: number, 
  tipo: 'sub-receita' | 'produto' | 'combo'
) {
  const response = await api.get('/receitas/itens', {
    params: { 
      receita_id: receitaId,
      tipo: tipo
    }
  });
  return response.data;
}
```

## Erros Possíveis

### 400 Bad Request
- Tipo inválido: Se o valor do parâmetro `tipo` não for um dos valores válidos

### 404 Not Found
- Receita não encontrada: Se o `receita_id` fornecido não existir

### 401 Unauthorized
- Token inválido ou ausente

## Notas

1. O parâmetro `tipo` é opcional. Se não for fornecido, retorna todos os tipos de itens.

2. O filtro por tipo é case-sensitive. Use exatamente: `sub-receita`, `produto` ou `combo`.

3. O campo `id` na resposta é o ID do vínculo na tabela `receita_ingrediente`, não o ID do item original. Use este ID para atualizar ou remover o item.

4. Para remover um item, use o endpoint:
   ```
   DELETE /api/catalogo/admin/receitas/itens/{id}
   ```
   Onde `{id}` é o `id` retornado neste endpoint.
