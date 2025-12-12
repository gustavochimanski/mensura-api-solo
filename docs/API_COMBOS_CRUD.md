# 📚 API - CRUD Completo de Combos

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [CREATE - Criar Combo](#create---criar-combo)
3. [READ - Listar Combos](#read---listar-combos)
4. [READ - Obter Combo por ID](#read---obter-combo-por-id)
5. [UPDATE - Atualizar Combo](#update---atualizar-combo)
6. [DELETE - Deletar Combo](#delete---deletar-combo)
7. [Exemplos de Implementação Front-end](#exemplos-de-implementação-front-end)
8. [Tratamento de Erros](#tratamento-de-erros)
9. [Validações e Regras de Negócio](#validações-e-regras-de-negócio)

---

## 🎯 Visão Geral

A API de Combos permite gerenciar combos de produtos de uma empresa. Cada combo pode conter múltiplos produtos com quantidades específicas.

### Base URL

```
/api/catalogo/admin/combos
```

### Autenticação

Todos os endpoints requerem autenticação via token JWT no header:

```http
Authorization: Bearer {token}
```

### Estrutura de Dados

#### Combo

```typescript
interface Combo {
  id: number;
  empresa_id: number;
  titulo: string;              // 1-120 caracteres
  descricao: string;            // 1-255 caracteres
  preco_total: number;          // >= 0, 2 casas decimais
  custo_total: number | null;  // >= 0, 2 casas decimais (opcional)
  ativo: boolean;
  imagem: string | null;        // URL da imagem (opcional)
  itens: ComboItem[];          // Lista de itens (obrigatório, mínimo 1)
  created_at: string;          // ISO 8601 datetime
  updated_at: string;          // ISO 8601 datetime
}
```

#### ComboItem

```typescript
interface ComboItem {
  produto_cod_barras: string;  // Código de barras do produto
  quantidade: number;           // >= 1
}
```

---

## ➕ CREATE - Criar Combo

### Endpoint

```http
POST /api/catalogo/admin/combos/
Authorization: Bearer {token}
Content-Type: multipart/form-data
```

### Parâmetros (Form Data)

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `empresa_id` | `int` | ✅ Sim | ID da empresa |
| `titulo` | `string` | ✅ Sim | Título do combo (1-120 caracteres) |
| `descricao` | `string` | ✅ Sim | Descrição do combo (1-255 caracteres) |
| `preco_total` | `float` | ✅ Sim | Preço total do combo (>= 0, 2 casas decimais) |
| `ativo` | `bool` | ❌ Não | Status ativo (padrão: `true`) |
| `itens` | `string` (JSON) | ✅ Sim | JSON array de itens: `[{"produto_cod_barras": "string", "quantidade": int}]` |
| `imagem` | `file` | ❌ Não | Arquivo de imagem (opcional) |

### Formato do JSON `itens`

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

### Exemplo de Requisição (cURL)

```bash
curl -X POST "https://api.exemplo.com/api/catalogo/admin/combos/" \
  -H "Authorization: Bearer {token}" \
  -F "empresa_id=1" \
  -F "titulo=Combo Pizza + Refrigerante" \
  -F "descricao=Pizza grande + 2 litros de refrigerante" \
  -F "preco_total=59.90" \
  -F "ativo=true" \
  -F 'itens=[{"produto_cod_barras":"7891234567890","quantidade":1},{"produto_cod_barras":"7891234567891","quantidade":2}]' \
  -F "imagem=@/caminho/para/imagem.jpg"
```

### Exemplo de Requisição (JavaScript/TypeScript)

```typescript
async function criarCombo(
  empresaId: number,
  titulo: string,
  descricao: string,
  precoTotal: number,
  itens: Array<{ produto_cod_barras: string; quantidade: number }>,
  ativo: boolean = true,
  imagem?: File
): Promise<Combo> {
  const formData = new FormData();
  formData.append('empresa_id', empresaId.toString());
  formData.append('titulo', titulo);
  formData.append('descricao', descricao);
  formData.append('preco_total', precoTotal.toString());
  formData.append('ativo', ativo.toString());
  formData.append('itens', JSON.stringify(itens));

  if (imagem) {
    formData.append('imagem', imagem);
  }

  const response = await fetch('/api/catalogo/admin/combos/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      // NÃO inclua Content-Type - o browser define automaticamente com boundary
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Erro ao criar combo: ${response.statusText}`);
  }

  return response.json();
}

// Exemplo de uso
const novoCombo = await criarCombo(
  1,
  'Combo Pizza + Refrigerante',
  'Pizza grande + 2 litros de refrigerante',
  59.90,
  [
    { produto_cod_barras: '7891234567890', quantidade: 1 },
    { produto_cod_barras: '7891234567891', quantidade: 2 },
  ],
  true,
  imagemFile // File object opcional
);
```

### Resposta de Sucesso

#### Status: `201 Created`

```json
{
  "id": 1,
  "empresa_id": 1,
  "titulo": "Combo Pizza + Refrigerante",
  "descricao": "Pizza grande + 2 litros de refrigerante",
  "preco_total": 59.90,
  "custo_total": null,
  "ativo": true,
  "imagem": "https://storage.exemplo.com/empresa-123/combos/uuid-imagem.jpg",
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
```

### Erros Possíveis

- **400 Bad Request**: Parâmetros inválidos ou JSON de itens inválido
- **404 Not Found**: Empresa não encontrada
- **422 Unprocessable Entity**: Validação falhou (título muito curto, preço negativo, etc.)

---

## 📖 READ - Listar Combos

### Endpoint

```http
GET /api/catalogo/admin/combos/
Authorization: Bearer {token}
```

### Parâmetros de Query

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `cod_empresa` | `int` | ✅ Sim | ID da empresa |
| `page` | `int` | ❌ Não | Número da página (padrão: `1`, mínimo: `1`) |
| `limit` | `int` | ❌ Não | Itens por página (padrão: `30`, mínimo: `1`, máximo: `100`) |
| `search` | `string` | ❌ Não | Termo de busca no título/descrição (case-insensitive) |

### Exemplo de Requisição

```http
GET /api/catalogo/admin/combos/?cod_empresa=1&page=1&limit=30&search=pizza
Authorization: Bearer {token}
```

### Exemplo de Implementação

```typescript
interface ListaCombosResponse {
  data: Combo[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

async function listarCombos(
  codEmpresa: number,
  page: number = 1,
  limit: number = 30,
  search?: string
): Promise<ListaCombosResponse> {
  const params = new URLSearchParams({
    cod_empresa: codEmpresa.toString(),
    page: page.toString(),
    limit: limit.toString(),
  });

  if (search && search.trim()) {
    params.append('search', search.trim());
  }

  const response = await fetch(
    `/api/catalogo/admin/combos/?${params.toString()}`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    }
  );

  if (!response.ok) {
    throw new Error(`Erro ao listar combos: ${response.statusText}`);
  }

  return response.json();
}
```

### Resposta de Sucesso

#### Status: `200 OK`

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
      "imagem": "https://storage.exemplo.com/empresa-123/combos/uuid-imagem.jpg",
      "itens": [
        {
          "produto_cod_barras": "7891234567890",
          "quantidade": 1
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

### Campos da Resposta

- `data`: Array de combos encontrados
- `total`: Total de combos encontrados (considerando filtros)
- `page`: Página atual
- `limit`: Itens por página
- `has_more`: Indica se há mais páginas disponíveis

---

## 🔍 READ - Obter Combo por ID

### Endpoint

```http
GET /api/catalogo/admin/combos/{combo_id}
Authorization: Bearer {token}
```

### Parâmetros de Path

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `combo_id` | `int` | ✅ Sim | ID do combo |

### Exemplo de Requisição

```http
GET /api/catalogo/admin/combos/1
Authorization: Bearer {token}
```

### Exemplo de Implementação

```typescript
async function obterCombo(comboId: number): Promise<Combo> {
  const response = await fetch(
    `/api/catalogo/admin/combos/${comboId}`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    }
  );

  if (response.status === 404) {
    throw new Error('Combo não encontrado');
  }

  if (!response.ok) {
    throw new Error(`Erro ao obter combo: ${response.statusText}`);
  }

  return response.json();
}
```

### Resposta de Sucesso

#### Status: `200 OK`

```json
{
  "id": 1,
  "empresa_id": 1,
  "titulo": "Combo Pizza + Refrigerante",
  "descricao": "Pizza grande + 2 litros de refrigerante",
  "preco_total": 59.90,
  "custo_total": 25.50,
  "ativo": true,
  "imagem": "https://storage.exemplo.com/empresa-123/combos/uuid-imagem.jpg",
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
```

### Erros Possíveis

- **404 Not Found**: Combo não encontrado

---

## ✏️ UPDATE - Atualizar Combo

### Endpoint

```http
PUT /api/catalogo/admin/combos/{combo_id}
Authorization: Bearer {token}
Content-Type: multipart/form-data
```

### Parâmetros de Path

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `combo_id` | `int` | ✅ Sim | ID do combo |

### Parâmetros (Form Data)

Todos os parâmetros são **opcionais**. Apenas os campos enviados serão atualizados.

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `titulo` | `string` | ❌ Não | Título do combo (1-120 caracteres) |
| `descricao` | `string` | ❌ Não | Descrição do combo (1-255 caracteres) |
| `preco_total` | `float` | ❌ Não | Preço total do combo (>= 0, 2 casas decimais) |
| `ativo` | `bool` | ❌ Não | Status ativo |
| `itens` | `string` (JSON) | ❌ Não | JSON array de itens (substitui TODOS os itens existentes) |
| `imagem` | `file` | ❌ Não | Nova imagem (substitui a imagem existente) |

### ⚠️ Importante sobre `itens`

- Se `itens` for enviado, **TODOS** os itens existentes serão **substituídos** pelos novos
- Se `itens` não for enviado, os itens existentes **permanecem inalterados**
- Para remover todos os itens, envie um array vazio: `[]` (mas isso pode causar erro de validação)

### Exemplo de Requisição (cURL)

```bash
curl -X PUT "https://api.exemplo.com/api/catalogo/admin/combos/1" \
  -H "Authorization: Bearer {token}" \
  -F "titulo=Combo Atualizado" \
  -F "preco_total=69.90" \
  -F "ativo=false"
```

### Exemplo de Implementação

```typescript
interface AtualizarComboParams {
  titulo?: string;
  descricao?: string;
  precoTotal?: number;
  ativo?: boolean;
  itens?: Array<{ produto_cod_barras: string; quantidade: number }>;
  imagem?: File;
}

async function atualizarCombo(
  comboId: number,
  params: AtualizarComboParams
): Promise<Combo> {
  const formData = new FormData();

  if (params.titulo !== undefined) {
    formData.append('titulo', params.titulo);
  }
  if (params.descricao !== undefined) {
    formData.append('descricao', params.descricao);
  }
  if (params.precoTotal !== undefined) {
    formData.append('preco_total', params.precoTotal.toString());
  }
  if (params.ativo !== undefined) {
    formData.append('ativo', params.ativo.toString());
  }
  if (params.itens !== undefined) {
    formData.append('itens', JSON.stringify(params.itens));
  }
  if (params.imagem) {
    formData.append('imagem', params.imagem);
  }

  const response = await fetch(
    `/api/catalogo/admin/combos/${comboId}`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    }
  );

  if (response.status === 404) {
    throw new Error('Combo não encontrado');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Erro ao atualizar combo: ${response.statusText}`);
  }

  return response.json();
}

// Exemplos de uso

// Atualizar apenas o título e preço
await atualizarCombo(1, {
  titulo: 'Combo Atualizado',
  precoTotal: 69.90,
});

// Atualizar status e itens
await atualizarCombo(1, {
  ativo: false,
  itens: [
    { produto_cod_barras: '7891234567890', quantidade: 2 },
  ],
});

// Atualizar imagem
await atualizarCombo(1, {
  imagem: novaImagemFile,
});

// Atualizar tudo
await atualizarCombo(1, {
  titulo: 'Novo Título',
  descricao: 'Nova Descrição',
  precoTotal: 79.90,
  ativo: true,
  itens: [
    { produto_cod_barras: '7891234567890', quantidade: 1 },
  ],
  imagem: novaImagemFile,
});
```

### Resposta de Sucesso

#### Status: `200 OK`

```json
{
  "id": 1,
  "empresa_id": 1,
  "titulo": "Combo Atualizado",
  "descricao": "Pizza grande + 2 litros de refrigerante",
  "preco_total": 69.90,
  "custo_total": 25.50,
  "ativo": false,
  "imagem": "https://storage.exemplo.com/empresa-123/combos/uuid-imagem.jpg",
  "itens": [
    {
      "produto_cod_barras": "7891234567890",
      "quantidade": 1
    }
  ],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T14:30:00Z"
}
```

### Erros Possíveis

- **400 Bad Request**: JSON de itens inválido ou parâmetros inválidos
- **404 Not Found**: Combo não encontrado
- **422 Unprocessable Entity**: Validação falhou

---

## 🗑️ DELETE - Deletar Combo

### Endpoint

```http
DELETE /api/catalogo/admin/combos/{combo_id}
Authorization: Bearer {token}
```

### Parâmetros de Path

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `combo_id` | `int` | ✅ Sim | ID do combo |

### Exemplo de Requisição

```http
DELETE /api/catalogo/admin/combos/1
Authorization: Bearer {token}
```

### Exemplo de Implementação

```typescript
async function deletarCombo(comboId: number): Promise<void> {
  const response = await fetch(
    `/api/catalogo/admin/combos/${comboId}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    }
  );

  if (response.status === 404) {
    throw new Error('Combo não encontrado');
  }

  if (!response.ok && response.status !== 204) {
    throw new Error(`Erro ao deletar combo: ${response.statusText}`);
  }

  // Status 204 No Content - sucesso sem corpo de resposta
}
```

### Resposta de Sucesso

#### Status: `204 No Content`

Sem corpo de resposta.

### Erros Possíveis

- **404 Not Found**: Combo não encontrado

---

## 💻 Exemplos de Implementação Front-end

### React Hook Completo

```typescript
import { useState, useCallback } from 'react';

interface UseCombosCRUDReturn {
  // Estado
  loading: boolean;
  error: string | null;
  
  // Operações
  criar: (params: CriarComboParams) => Promise<Combo>;
  listar: (params: ListarCombosParams) => Promise<ListaCombosResponse>;
  obter: (comboId: number) => Promise<Combo>;
  atualizar: (comboId: number, params: AtualizarComboParams) => Promise<Combo>;
  deletar: (comboId: number) => Promise<void>;
}

interface CriarComboParams {
  empresaId: number;
  titulo: string;
  descricao: string;
  precoTotal: number;
  itens: Array<{ produto_cod_barras: string; quantidade: number }>;
  ativo?: boolean;
  imagem?: File;
}

interface ListarCombosParams {
  codEmpresa: number;
  page?: number;
  limit?: number;
  search?: string;
}

function useCombosCRUD(): UseCombosCRUDReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const criar = useCallback(async (params: CriarComboParams): Promise<Combo> => {
    setLoading(true);
    setError(null);
    try {
      return await criarCombo(
        params.empresaId,
        params.titulo,
        params.descricao,
        params.precoTotal,
        params.itens,
        params.ativo ?? true,
        params.imagem
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao criar combo';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const listar = useCallback(async (params: ListarCombosParams): Promise<ListaCombosResponse> => {
    setLoading(true);
    setError(null);
    try {
      return await listarCombos(
        params.codEmpresa,
        params.page,
        params.limit,
        params.search
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao listar combos';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const obter = useCallback(async (comboId: number): Promise<Combo> => {
    setLoading(true);
    setError(null);
    try {
      return await obterCombo(comboId);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao obter combo';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const atualizar = useCallback(async (
    comboId: number,
    params: AtualizarComboParams
  ): Promise<Combo> => {
    setLoading(true);
    setError(null);
    try {
      return await atualizarCombo(comboId, params);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao atualizar combo';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const deletar = useCallback(async (comboId: number): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      await deletarCombo(comboId);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao deletar combo';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    criar,
    listar,
    obter,
    atualizar,
    deletar,
  };
}

// Exemplo de uso no componente
function CombosPage() {
  const { criar, listar, obter, atualizar, deletar, loading, error } = useCombosCRUD();
  const [combos, setCombos] = useState<Combo[]>([]);

  const handleCriar = async () => {
    try {
      const novoCombo = await criar({
        empresaId: 1,
        titulo: 'Novo Combo',
        descricao: 'Descrição do combo',
        precoTotal: 59.90,
        itens: [
          { produto_cod_barras: '7891234567890', quantidade: 1 },
        ],
      });
      // Atualizar lista ou redirecionar
      console.log('Combo criado:', novoCombo);
    } catch (err) {
      console.error('Erro:', err);
    }
  };

  // ... outros handlers

  return (
    <div>
      {loading && <p>Carregando...</p>}
      {error && <p>Erro: {error}</p>}
      {/* UI do componente */}
    </div>
  );
}
```

### Componente React Completo

```typescript
import React, { useState, useEffect } from 'react';

function ComboForm({ comboId, onSuccess }: { comboId?: number; onSuccess?: () => void }) {
  const { criar, atualizar, obter, loading } = useCombosCRUD();
  const [formData, setFormData] = useState({
    empresaId: 1,
    titulo: '',
    descricao: '',
    precoTotal: 0,
    ativo: true,
    itens: [] as Array<{ produto_cod_barras: string; quantidade: number }>,
  });
  const [imagem, setImagem] = useState<File | null>(null);

  useEffect(() => {
    if (comboId) {
      obter(comboId).then((combo) => {
        setFormData({
          empresaId: combo.empresa_id,
          titulo: combo.titulo,
          descricao: combo.descricao,
          precoTotal: combo.preco_total,
          ativo: combo.ativo,
          itens: combo.itens,
        });
      });
    }
  }, [comboId, obter]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      if (comboId) {
        await atualizar(comboId, {
          ...formData,
          imagem: imagem || undefined,
        });
      } else {
        await criar({
          ...formData,
          imagem: imagem || undefined,
        });
      }
      onSuccess?.();
    } catch (err) {
      console.error('Erro ao salvar:', err);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Título"
        value={formData.titulo}
        onChange={(e) => setFormData({ ...formData, titulo: e.target.value })}
        required
      />
      <textarea
        placeholder="Descrição"
        value={formData.descricao}
        onChange={(e) => setFormData({ ...formData, descricao: e.target.value })}
        required
      />
      <input
        type="number"
        step="0.01"
        placeholder="Preço Total"
        value={formData.precoTotal}
        onChange={(e) => setFormData({ ...formData, precoTotal: parseFloat(e.target.value) })}
        required
      />
      <input
        type="file"
        accept="image/*"
        onChange={(e) => setImagem(e.target.files?.[0] || null)}
      />
      <button type="submit" disabled={loading}>
        {loading ? 'Salvando...' : comboId ? 'Atualizar' : 'Criar'}
      </button>
    </form>
  );
}
```

---

## 🚨 Tratamento de Erros

### Códigos de Status HTTP

| Código | Descrição | Quando Ocorre |
|--------|-----------|---------------|
| `200` | OK | Operação bem-sucedida (GET, PUT) |
| `201` | Created | Combo criado com sucesso (POST) |
| `204` | No Content | Combo deletado com sucesso (DELETE) |
| `400` | Bad Request | Parâmetros inválidos ou JSON malformado |
| `401` | Unauthorized | Token ausente ou inválido |
| `404` | Not Found | Combo ou empresa não encontrado |
| `422` | Unprocessable Entity | Validação falhou (campos inválidos) |
| `500` | Internal Server Error | Erro interno do servidor |

### Exemplo de Tratamento Completo

```typescript
async function criarComboComTratamento(
  empresaId: number,
  titulo: string,
  descricao: string,
  precoTotal: number,
  itens: Array<{ produto_cod_barras: string; quantidade: number }>,
  imagem?: File
): Promise<Combo> {
  try {
    // Validações client-side
    if (!titulo || titulo.length < 1 || titulo.length > 120) {
      throw new Error('Título deve ter entre 1 e 120 caracteres');
    }
    if (!descricao || descricao.length < 1 || descricao.length > 255) {
      throw new Error('Descrição deve ter entre 1 e 255 caracteres');
    }
    if (precoTotal < 0) {
      throw new Error('Preço total deve ser maior ou igual a zero');
    }
    if (!itens || itens.length === 0) {
      throw new Error('Combo deve ter pelo menos um item');
    }

    const formData = new FormData();
    formData.append('empresa_id', empresaId.toString());
    formData.append('titulo', titulo);
    formData.append('descricao', descricao);
    formData.append('preco_total', precoTotal.toString());
    formData.append('ativo', 'true');
    formData.append('itens', JSON.stringify(itens));

    if (imagem) {
      formData.append('imagem', imagem);
    }

    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('Token de autenticação não encontrado');
    }

    const response = await fetch('/api/catalogo/admin/combos/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    // Tratamento de erros específicos
    if (response.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
      throw new Error('Sessão expirada. Faça login novamente.');
    }

    if (response.status === 404) {
      throw new Error('Empresa não encontrada');
    }

    if (response.status === 422) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Validação falhou');
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `Erro ao criar combo: ${response.statusText}`
      );
    }

    return response.json();
  } catch (error) {
    console.error('Erro ao criar combo:', error);
    throw error;
  }
}
```

---

## ✅ Validações e Regras de Negócio

### Validações de Campos

#### `titulo`
- **Obrigatório**: Sim (ao criar)
- **Tipo**: String
- **Tamanho**: 1-120 caracteres
- **Validação**: Não pode ser vazio

#### `descricao`
- **Obrigatório**: Sim (ao criar)
- **Tipo**: String
- **Tamanho**: 1-255 caracteres
- **Validação**: Não pode ser vazio

#### `preco_total`
- **Obrigatório**: Sim (ao criar)
- **Tipo**: Float/Decimal
- **Formato**: 2 casas decimais
- **Validação**: >= 0

#### `custo_total`
- **Obrigatório**: Não
- **Tipo**: Float/Decimal
- **Formato**: 2 casas decimais
- **Validação**: >= 0 (se informado)

#### `ativo`
- **Obrigatório**: Não
- **Tipo**: Boolean
- **Padrão**: `true`

#### `itens`
- **Obrigatório**: Sim (ao criar)
- **Tipo**: Array de objetos
- **Validação**: 
  - Mínimo 1 item
  - Cada item deve ter `produto_cod_barras` (string não vazia)
  - Cada item deve ter `quantidade` (>= 1)
  - `produto_cod_barras` deve existir no banco de dados

#### `imagem`
- **Obrigatório**: Não
- **Tipo**: File (imagem)
- **Formatos aceitos**: JPG, PNG, GIF, WebP
- **Tamanho máximo**: Verificar configuração do servidor (geralmente 5-10MB)

### Regras de Negócio

1. **Empresa**: O combo deve pertencer a uma empresa válida
2. **Itens**: Todos os produtos referenciados em `itens` devem existir
3. **Imagem**: Se uma nova imagem for enviada no UPDATE, a imagem antiga será substituída
4. **Itens no UPDATE**: Se `itens` for enviado no UPDATE, todos os itens existentes serão substituídos
5. **Soft Delete**: A exclusão pode ser lógica (verificar implementação)

---

## 📝 Notas Importantes

### Upload de Imagens

- As imagens são armazenadas no MinIO/S3
- A URL da imagem é gerada automaticamente após o upload
- O formato do nome do arquivo é: `{slug}/{uuid}.{extensão}`
- O slug para combos é: `combos`

### Formato de Data

- Todas as datas são retornadas no formato ISO 8601: `YYYY-MM-DDTHH:mm:ssZ`
- Exemplo: `2024-01-15T10:30:00Z`

### Paginação

- A paginação é baseada em offset/limit
- Use `has_more` para verificar se há mais páginas
- Ordenação padrão: `created_at DESC` (mais recentes primeiro)

### Busca

- A busca é case-insensitive
- Busca parcial (substring) em `título` e `descricao`
- A busca é aplicada no banco de dados (não no cliente)

---

## 🔗 Endpoints Relacionados

- **Listar Produtos**: `GET /api/catalogo/admin/produtos/` (para obter códigos de barras)
- **Busca Global**: `GET /api/catalogo/admin/busca/global` (busca em produtos, receitas e combos)

---

## 📅 Última Atualização

Documentação atualizada em: Janeiro 2024

**Base URL**: `/api/catalogo/admin/combos`

**Autenticação**: Requer token JWT de admin (via `Authorization: Bearer {token}`)

