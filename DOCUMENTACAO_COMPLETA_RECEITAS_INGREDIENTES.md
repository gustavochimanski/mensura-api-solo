# 📚 Documentação Completa: Sistema de Receitas e Ingredientes

## 🎯 Visão Geral

O sistema de **Receitas e Ingredientes** permite gerenciar receitas e seus ingredientes de forma independente. Cada ingrediente pode ser usado em múltiplas receitas, e cada receita pode ter múltiplos ingredientes (relacionamento N:N).

### Conceitos Principais

1. **Ingredientes** - Cadastro independente de ingredientes com informações próprias (nome, descrição, unidade, custo)
2. **Receitas** - Receitas que utilizam ingredientes em suas composições
3. **ReceitaIngrediente** - Relacionamento entre receita e ingrediente com quantidade específica
4. **Adicionais** - Produtos adicionais que podem ser vinculados a receitas

### ⚠️ Regra Fundamental: Relacionamento N:N

**Um ingrediente pode estar em várias receitas, e uma receita pode ter vários ingredientes:**
- Um ingrediente cadastrado pode ser reutilizado em múltiplas receitas
- Cada receita pode ter múltiplos ingredientes
- Cada vínculo receita-ingrediente tem sua própria quantidade
- Evita duplicação de dados e permite reutilização eficiente

---

## 📊 Estrutura de Dados

### 1. IngredienteModel (`catalogo.ingredientes`)

Tabela independente para cadastro de ingredientes.

```python
{
    id: int                          # PK, auto-incremento
    empresa_id: int                  # ID da empresa
    nome: string(100)                # Nome do ingrediente (ex: "Farinha", "Açúcar")
    descricao: string(255)           # Descrição opcional
    unidade_medida: string(10)       # Unidade (ex: "KG", "L", "UN", "GR")
    custo: decimal(18,2)             # Custo do ingrediente (OBRIGATÓRIO)
    ativo: boolean                   # Status ativo/inativo
    created_at: datetime
    updated_at: datetime
}
```

### 2. ReceitaModel (`catalogo.receitas`)

Tabela de receitas.

```python
{
    id: int                          # PK, auto-incremento
    empresa_id: int                  # FK: cadastros.empresas.id
    nome: string(100)                # Nome da receita
    descricao: string(255)           # Descrição opcional
    preco_venda: decimal(18,2)       # Preço de venda
    imagem: string(500)              # URL da imagem
    ativo: boolean                   # Status ativo/inativo
    disponivel: boolean              # Disponibilidade
    created_at: datetime
    updated_at: datetime
}
```

### 3. ReceitaIngredienteModel (`catalogo.receita_ingrediente`)

Tabela de relacionamento N:N entre receitas e ingredientes.

```python
{
    id: int                          # PK, auto-incremento
    receita_id: int                  # FK: catalogo.receitas.id
    ingrediente_id: int              # FK: catalogo.ingredientes.id
    quantidade: decimal(18,4)        # Quantidade do ingrediente
}
```

**Nota:** Não há constraint UNIQUE em `ingrediente_id`, permitindo que um ingrediente esteja em várias receitas.

### 4. ReceitaAdicionalModel (`catalogo.receita_adicional`)

Tabela de relacionamento entre receitas e adicionais (produtos).

```python
{
    id: int                          # PK, auto-incremento
    receita_id: int                  # FK: catalogo.receitas.id
    adicional_cod_barras: string     # FK: catalogo.produtos.cod_barras
    preco: decimal(18,2)             # Preço do adicional
}
```

---

## 🔗 Relacionamentos

```
Empresa
  ├── Ingrediente (1:N) - Um ingrediente pertence a uma empresa
  └── Receita (1:N) - Uma receita pertence a uma empresa

Receita (1) ────< (N) ReceitaIngredienteModel >─── (1) Ingrediente
  └── Relacionamento N:N (um ingrediente pode estar em várias receitas)

Receita (1) ────< (N) ReceitaAdicionalModel >─── (1) Produto
```

---

## 🛣️ Rotas e Endpoints

### Base URL
- **Ingredientes:** `/api/catalogo/admin/receitas/ingredientes`
- **Receitas:** `/api/catalogo/admin/receitas`
- **Receitas com Ingredientes:** `/api/catalogo/admin/receitas/com-ingredientes`
- **Compatibilidade (Legado):** `/api/cadastros/admin/receitas`

---

## 📋 Schemas e Responses

### Schemas de Ingrediente

#### CriarIngredienteRequest
```typescript
{
  empresa_id: number;                    // OBRIGATÓRIO
  nome: string;                          // OBRIGATÓRIO, min 1, max 100 caracteres
  descricao?: string;                    // Opcional, max 255 caracteres
  unidade_medida?: string;               // Opcional, max 10 caracteres (ex: "KG", "L", "UN", "GR")
  custo: number;                         // OBRIGATÓRIO, decimal(18,2), padrão: 0
  ativo?: boolean;                       // Opcional, padrão: true
}
```

#### AtualizarIngredienteRequest
```typescript
{
  nome?: string;                         // Opcional, min 1, max 100 caracteres
  descricao?: string;                    // Opcional, max 255 caracteres
  unidade_medida?: string;               // Opcional, max 10 caracteres
  custo?: number;                        // Opcional, decimal(18,2)
  ativo?: boolean;                       // Opcional
}
```

#### IngredienteResponse
```typescript
{
  id: number;
  empresa_id: number;
  nome: string;
  descricao?: string | null;
  unidade_medida?: string | null;
  custo: number;                         // decimal(18,2)
  ativo: boolean;
  created_at: string;                    // ISO datetime
  updated_at: string;                    // ISO datetime
}
```

#### IngredienteResumidoResponse
```typescript
{
  id: number;
  nome: string;
  unidade_medida?: string | null;
  custo: number;                         // decimal(18,2)
  ativo: boolean;
}
```

### Schemas de Receita

#### ReceitaIn
```typescript
{
  empresa_id: number;                    // OBRIGATÓRIO
  nome: string;                          // OBRIGATÓRIO, min 1, max 100 caracteres
  descricao?: string;                    // Opcional
  preco_venda: number;                   // OBRIGATÓRIO, decimal(18,2)
  imagem?: string;                       // Opcional
  ativo?: boolean;                       // Opcional, padrão: true
  disponivel?: boolean;                  // Opcional, padrão: true
}
```

#### ReceitaUpdate
```typescript
{
  nome?: string;                         // Opcional, max 100 caracteres
  descricao?: string;                    // Opcional
  preco_venda?: number;                  // Opcional, decimal(18,2)
  imagem?: string;                       // Opcional
  ativo?: boolean;                       // Opcional
  disponivel?: boolean;                  // Opcional
}
```

#### ReceitaOut
```typescript
{
  id: number;
  empresa_id: number;
  nome: string;
  descricao?: string | null;
  preco_venda: number;                   // decimal(18,2)
  imagem?: string | null;
  ativo: boolean;
  disponivel: boolean;
  created_at: string;                    // ISO datetime
  updated_at: string;                    // ISO datetime
}
```

#### ReceitaIngredienteIn
```typescript
{
  receita_id: number;                    // OBRIGATÓRIO
  ingrediente_id: number;                // OBRIGATÓRIO
  quantidade?: number;                   // Opcional, decimal(18,4)
}
```

#### ReceitaIngredienteOut
```typescript
{
  id: number;
  receita_id: number;
  ingrediente_id: number;
  quantidade?: number | null;            // decimal(18,4)
}
```

#### ReceitaIngredienteDetalhadoOut
```typescript
{
  id: number;
  receita_id: number;
  ingrediente_id: number;
  quantidade?: number | null;            // decimal(18,4)
  // Dados do ingrediente
  ingrediente_nome?: string | null;
  ingrediente_descricao?: string | null;
  ingrediente_unidade_medida?: string | null;
  ingrediente_custo?: number | null;     // decimal(18,2)
}
```

#### ReceitaComIngredientesOut
```typescript
{
  id: number;
  empresa_id: number;
  nome: string;
  descricao?: string | null;
  preco_venda: number;                   // decimal(18,2)
  imagem?: string | null;
  ativo: boolean;
  disponivel: boolean;
  created_at: string;                    // ISO datetime
  updated_at: string;                    // ISO datetime
  ingredientes: ReceitaIngredienteDetalhadoOut[];  // Lista de ingredientes detalhados
}
```

#### AdicionalIn
```typescript
{
  receita_id: number;                    // OBRIGATÓRIO
  adicional_cod_barras: string;          // OBRIGATÓRIO, min 1 caractere
  preco?: number;                        // Opcional, decimal(18,2)
}
```

#### AdicionalOut
```typescript
{
  id: number;
  receita_id: number;
  adicional_cod_barras: string;
  preco?: number | null;                 // decimal(18,2)
}
```

---

## 🔌 Endpoints Detalhados

### 🔹 Ingredientes

#### 1. Listar Ingredientes
```http
GET /api/catalogo/admin/receitas/ingredientes/
```

**Query Parameters:**
- `empresa_id` (obrigatório): ID da empresa
- `apenas_ativos` (opcional, padrão: `true`): Filtrar apenas ingredientes ativos

**Response:** `IngredienteResponse[]`

**Exemplo:**
```http
GET /api/catalogo/admin/receitas/ingredientes/?empresa_id=1&apenas_ativos=true
```

**Resposta:**
```json
[
  {
    "id": 1,
    "empresa_id": 1,
    "nome": "Farinha de Trigo",
    "descricao": "Farinha tipo 1",
    "unidade_medida": "KG",
    "custo": 5.50,
    "ativo": true,
    "created_at": "2025-01-18T10:00:00Z",
    "updated_at": "2025-01-18T10:00:00Z"
  }
]
```

---

#### 2. Criar Ingrediente
```http
POST /api/catalogo/admin/receitas/ingredientes/
```

**Body:** `CriarIngredienteRequest`

**Response:** `IngredienteResponse` (201 Created)

**Exemplo:**
```json
{
  "empresa_id": 1,
  "nome": "Açúcar Cristal",
  "descricao": "Açúcar refinado",
  "unidade_medida": "KG",
  "custo": 3.80,
  "ativo": true
}
```

---

#### 3. Buscar Ingrediente por ID
```http
GET /api/catalogo/admin/receitas/ingredientes/{ingrediente_id}
```

**Path Parameters:**
- `ingrediente_id`: ID do ingrediente

**Response:** `IngredienteResponse`

**Exemplo:**
```http
GET /api/catalogo/admin/receitas/ingredientes/1
```

---

#### 4. Atualizar Ingrediente
```http
PUT /api/catalogo/admin/receitas/ingredientes/{ingrediente_id}
```

**Path Parameters:**
- `ingrediente_id`: ID do ingrediente

**Body:** `AtualizarIngredienteRequest`

**Response:** `IngredienteResponse`

**Exemplo:**
```json
{
  "nome": "Farinha de Trigo Tipo 00",
  "custo": 6.00
}
```

---

#### 5. Deletar Ingrediente
```http
DELETE /api/catalogo/admin/receitas/ingredientes/{ingrediente_id}
```

**Path Parameters:**
- `ingrediente_id`: ID do ingrediente

**Response:** `200 OK` com mensagem

**Regra:** Não é possível deletar ingrediente que está vinculado a uma ou mais receitas. Remova o ingrediente das receitas antes de deletar.

**Erro 400:** `"Não é possível deletar ingrediente que está vinculado a uma ou mais receitas. Remova o ingrediente das receitas antes de deletar."`

---

### 🔹 Receitas

#### 6. Listar Receitas
```http
GET /api/catalogo/admin/receitas/
```

**Query Parameters:**
- `empresa_id` (opcional): Filtrar por empresa
- `ativo` (opcional): Filtrar por status ativo/inativo

**Response:** `ReceitaOut[]`

**Exemplo:**
```http
GET /api/catalogo/admin/receitas/?empresa_id=1&ativo=true
```

---

#### 7. Listar Receitas com Ingredientes ⭐ NOVO
```http
GET /api/catalogo/admin/receitas/com-ingredientes
```

**Query Parameters:**
- `empresa_id` (opcional): Filtrar por empresa
- `ativo` (opcional): Filtrar por status ativo/inativo

**Response:** `ReceitaComIngredientesOut[]`

**Exemplo:**
```http
GET /api/catalogo/admin/receitas/com-ingredientes?empresa_id=1&ativo=true
```

**Resposta:**
```json
[
  {
    "id": 1,
    "empresa_id": 1,
    "nome": "Pizza Margherita",
    "descricao": "Pizza clássica italiana",
    "preco_venda": 25.00,
    "imagem": "https://example.com/pizza.jpg",
    "ativo": true,
    "disponivel": true,
    "created_at": "2025-01-18T10:00:00Z",
    "updated_at": "2025-01-18T10:00:00Z",
    "ingredientes": [
      {
        "id": 1,
        "receita_id": 1,
        "ingrediente_id": 5,
        "quantidade": 2.5,
        "ingrediente_nome": "Farinha de Trigo",
        "ingrediente_descricao": "Farinha tipo 1",
        "ingrediente_unidade_medida": "KG",
        "ingrediente_custo": 5.50
      },
      {
        "id": 2,
        "receita_id": 1,
        "ingrediente_id": 8,
        "quantidade": 0.5,
        "ingrediente_nome": "Tomate",
        "ingrediente_descricao": "Tomate fresco",
        "ingrediente_unidade_medida": "KG",
        "ingrediente_custo": 4.00
      }
    ]
  }
]
```

---

#### 8. Criar Receita
```http
POST /api/catalogo/admin/receitas/
```

**Body:** `ReceitaIn`

**Response:** `ReceitaOut` (201 Created)

**Exemplo:**
```json
{
  "empresa_id": 1,
  "nome": "Pizza Margherita",
  "descricao": "Pizza clássica italiana",
  "preco_venda": 25.00,
  "imagem": "https://example.com/pizza.jpg",
  "ativo": true,
  "disponivel": true
}
```

---

#### 9. Buscar Receita por ID
```http
GET /api/catalogo/admin/receitas/{receita_id}
```

**Path Parameters:**
- `receita_id`: ID da receita

**Response:** `ReceitaOut`

---

#### 10. Atualizar Receita
```http
PUT /api/catalogo/admin/receitas/{receita_id}
```

**Path Parameters:**
- `receita_id`: ID da receita

**Body:** `ReceitaUpdate`

**Response:** `ReceitaOut`

---

#### 11. Deletar Receita
```http
DELETE /api/catalogo/admin/receitas/{receita_id}
```

**Path Parameters:**
- `receita_id`: ID da receita

**Response:** `204 No Content`

**Nota:** Deletar uma receita também deleta todos os seus ingredientes e adicionais vinculados (cascade).

---

### 🔹 Ingredientes de Receitas (Vinculação)

#### 12. Listar Ingredientes de uma Receita
```http
GET /api/catalogo/admin/receitas/{receita_id}/ingredientes
```

**Path Parameters:**
- `receita_id`: ID da receita

**Response:** `ReceitaIngredienteOut[]`

**Exemplo:**
```http
GET /api/catalogo/admin/receitas/1/ingredientes
```

**Resposta:**
```json
[
  {
    "id": 1,
    "receita_id": 1,
    "ingrediente_id": 5,
    "quantidade": 2.5
  },
  {
    "id": 2,
    "receita_id": 1,
    "ingrediente_id": 8,
    "quantidade": 0.5
  }
]
```

---

#### 13. Adicionar Ingrediente a Receita
```http
POST /api/catalogo/admin/receitas/ingredientes
```

**Body:** `ReceitaIngredienteIn`

**Response:** `ReceitaIngredienteOut` (201 Created)

**Exemplo:**
```json
{
  "receita_id": 1,
  "ingrediente_id": 5,
  "quantidade": 2.5
}
```

**Regra:** Não é possível adicionar o mesmo ingrediente duas vezes na mesma receita (retorna erro 400).

**Erro 400:** `"Ingrediente já cadastrado nesta receita"`

---

#### 14. Atualizar Quantidade de Ingrediente na Receita
```http
PUT /api/catalogo/admin/receitas/ingredientes/{receita_ingrediente_id}
```

**Path Parameters:**
- `receita_ingrediente_id`: ID do vínculo receita-ingrediente

**Body:**
```json
{
  "quantidade": 3.0
}
```

**Response:** `ReceitaIngredienteOut`

---

#### 15. Remover Ingrediente de Receita
```http
DELETE /api/catalogo/admin/receitas/ingredientes/{receita_ingrediente_id}
```

**Path Parameters:**
- `receita_ingrediente_id`: ID do vínculo receita-ingrediente

**Response:** `204 No Content`

**Nota:** Remove apenas o vínculo, não deleta o ingrediente em si.

---

### 🔹 Adicionais de Receitas

#### 16. Listar Adicionais de uma Receita
```http
GET /api/catalogo/admin/receitas/{receita_id}/adicionais
```

**Path Parameters:**
- `receita_id`: ID da receita

**Response:** `AdicionalOut[]`

---

#### 17. Adicionar Adicional a Receita
```http
POST /api/catalogo/admin/receitas/adicionais
```

**Body:** `AdicionalIn`

**Response:** `AdicionalOut` (201 Created)

**Exemplo:**
```json
{
  "receita_id": 1,
  "adicional_cod_barras": "7891234567890",
  "preco": 5.00
}
```

---

#### 18. Atualizar Preço de Adicional
```http
PUT /api/catalogo/admin/receitas/adicionais/{adicional_id}
```

**Path Parameters:**
- `adicional_id`: ID do adicional

**Body:**
```json
{
  "preco": 6.00
}
```

**Response:** `AdicionalOut`

---

#### 19. Remover Adicional de Receita
```http
DELETE /api/catalogo/admin/receitas/adicionais/{adicional_id}
```

**Path Parameters:**
- `adicional_id`: ID do adicional

**Response:** `204 No Content`

---

## 🔄 Fluxo de Trabalho Recomendado

### 1. Cadastrar Ingredientes Primeiro

```javascript
// 1. Criar ingrediente
const ingrediente1 = await criarIngrediente({
  empresa_id: 1,
  nome: "Farinha de Trigo",
  descricao: "Farinha tipo 1",
  unidade_medida: "KG",
  custo: 5.50,
  ativo: true
});

const ingrediente2 = await criarIngrediente({
  empresa_id: 1,
  nome: "Tomate",
  descricao: "Tomate fresco",
  unidade_medida: "KG",
  custo: 4.00,
  ativo: true
});
```

### 2. Criar Receita

```javascript
// 2. Criar receita
const receita = await criarReceita({
  empresa_id: 1,
  nome: "Pizza Margherita",
  descricao: "Pizza clássica italiana",
  preco_venda: 25.00,
  imagem: "https://example.com/pizza.jpg",
  ativo: true,
  disponivel: true
});
```

### 3. Vincular Ingredientes à Receita

```javascript
// 3. Adicionar ingredientes à receita
await adicionarIngredienteAReceita({
  receita_id: receita.id,
  ingrediente_id: ingrediente1.id,
  quantidade: 2.5
});

await adicionarIngredienteAReceita({
  receita_id: receita.id,
  ingrediente_id: ingrediente2.id,
  quantidade: 0.5
});
```

### 4. Listar Receitas com Ingredientes

```javascript
// 4. Listar receitas com ingredientes (mais eficiente)
const receitasComIngredientes = await listarReceitasComIngredientes({
  empresa_id: 1,
  ativo: true
});

// Recebe tudo de uma vez, sem precisar fazer múltiplas chamadas
receitasComIngredientes.forEach(receita => {
  console.log(`Receita: ${receita.nome}`);
  receita.ingredientes.forEach(ing => {
    console.log(`  - ${ing.ingrediente_nome}: ${ing.quantidade} ${ing.ingrediente_unidade_medida}`);
    console.log(`    Custo: R$ ${ing.ingrediente_custo}`);
  });
});
```

---

## ⚠️ Regras de Negócio Importantes

### Ingredientes

1. **Custo Obrigatório:** Todo ingrediente deve ter um custo (padrão: 0)
2. **Empresa:** Cada ingrediente pertence a uma empresa
3. **Reutilização:** Um ingrediente pode estar em múltiplas receitas
4. **Exclusão:** Não é possível deletar ingrediente vinculado a receitas

### Receitas

1. **Empresa:** Cada receita pertence a uma empresa
2. **Preço de Venda:** Deve ser informado ao criar
3. **Cascade Delete:** Deletar receita deleta todos os ingredientes e adicionais vinculados

### Vinculação Receita-Ingrediente

1. **Sem Duplicatas:** Não é possível adicionar o mesmo ingrediente duas vezes na mesma receita
2. **Quantidade Opcional:** A quantidade pode ser nula
3. **Relacionamento N:N:** Um ingrediente pode estar em várias receitas, uma receita pode ter vários ingredientes

---

## 🎨 Exemplos de Integração Frontend

### React/TypeScript - Exemplo Completo

```typescript
// types.ts
interface Ingrediente {
  id: number;
  empresa_id: number;
  nome: string;
  descricao?: string | null;
  unidade_medida?: string | null;
  custo: number;
  ativo: boolean;
  created_at: string;
  updated_at: string;
}

interface ReceitaIngrediente {
  id: number;
  receita_id: number;
  ingrediente_id: number;
  quantidade?: number | null;
  ingrediente_nome?: string | null;
  ingrediente_descricao?: string | null;
  ingrediente_unidade_medida?: string | null;
  ingrediente_custo?: number | null;
}

interface Receita {
  id: number;
  empresa_id: number;
  nome: string;
  descricao?: string | null;
  preco_venda: number;
  imagem?: string | null;
  ativo: boolean;
  disponivel: boolean;
  created_at: string;
  updated_at: string;
  ingredientes?: ReceitaIngrediente[];
}

// api.ts
const API_BASE = '/api/catalogo/admin/receitas';

export const ingredientesApi = {
  listar: async (empresaId: number, apenasAtivos = true): Promise<Ingrediente[]> => {
    const response = await fetch(
      `${API_BASE}/ingredientes/?empresa_id=${empresaId}&apenas_ativos=${apenasAtivos}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return response.json();
  },

  criar: async (data: CriarIngredienteRequest): Promise<Ingrediente> => {
    const response = await fetch(`${API_BASE}/ingredientes/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(data)
    });
    return response.json();
  },

  buscar: async (id: number): Promise<Ingrediente> => {
    const response = await fetch(`${API_BASE}/ingredientes/${id}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.json();
  },

  atualizar: async (id: number, data: AtualizarIngredienteRequest): Promise<Ingrediente> => {
    const response = await fetch(`${API_BASE}/ingredientes/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(data)
    });
    return response.json();
  },

  deletar: async (id: number): Promise<void> => {
    await fetch(`${API_BASE}/ingredientes/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    });
  }
};

export const receitasApi = {
  listar: async (empresaId?: number, ativo?: boolean): Promise<Receita[]> => {
    const params = new URLSearchParams();
    if (empresaId) params.append('empresa_id', empresaId.toString());
    if (ativo !== undefined) params.append('ativo', ativo.toString());
    
    const response = await fetch(`${API_BASE}/?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.json();
  },

  listarComIngredientes: async (empresaId?: number, ativo?: boolean): Promise<Receita[]> => {
    const params = new URLSearchParams();
    if (empresaId) params.append('empresa_id', empresaId.toString());
    if (ativo !== undefined) params.append('ativo', ativo.toString());
    
    const response = await fetch(`${API_BASE}/com-ingredientes?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.json();
  },

  criar: async (data: ReceitaIn): Promise<Receita> => {
    const response = await fetch(`${API_BASE}/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(data)
    });
    return response.json();
  },

  buscar: async (id: number): Promise<Receita> => {
    const response = await fetch(`${API_BASE}/${id}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.json();
  },

  listarIngredientes: async (receitaId: number): Promise<ReceitaIngrediente[]> => {
    const response = await fetch(`${API_BASE}/${receitaId}/ingredientes`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.json();
  },

  adicionarIngrediente: async (data: ReceitaIngredienteIn): Promise<ReceitaIngrediente> => {
    const response = await fetch(`${API_BASE}/ingredientes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(data)
    });
    return response.json();
  },

  removerIngrediente: async (receitaIngredienteId: number): Promise<void> => {
    await fetch(`${API_BASE}/ingredientes/${receitaIngredienteId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    });
  }
};

// Componente React - Exemplo de uso
const ReceitasPage: React.FC = () => {
  const [receitas, setReceitas] = React.useState<Receita[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const carregarReceitas = async () => {
      setLoading(true);
      try {
        // Usar listarComIngredientes para receber tudo de uma vez
        const data = await receitasApi.listarComIngredientes(1, true);
        setReceitas(data);
      } catch (error) {
        console.error('Erro ao carregar receitas:', error);
      } finally {
        setLoading(false);
      }
    };

    carregarReceitas();
  }, []);

  if (loading) return <div>Carregando...</div>;

  return (
    <div>
      {receitas.map(receita => (
        <div key={receita.id}>
          <h2>{receita.nome}</h2>
          <p>Preço: R$ {receita.preco_venda}</p>
          <h3>Ingredientes:</h3>
          <ul>
            {receita.ingredientes?.map(ing => (
              <li key={ing.id}>
                {ing.ingrediente_nome}: {ing.quantidade} {ing.ingrediente_unidade_medida}
                <br />
                <small>Custo: R$ {ing.ingrediente_custo}</small>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
};
```

---

## 📝 Códigos de Status HTTP

- `200 OK` - Sucesso
- `201 Created` - Recurso criado com sucesso
- `204 No Content` - Sucesso sem conteúdo (delete)
- `400 Bad Request` - Requisição inválida (ex: ingrediente já vinculado)
- `404 Not Found` - Recurso não encontrado
- `422 Unprocessable Entity` - Erro de validação

---

## 🔒 Autenticação

Todos os endpoints requerem autenticação via Bearer Token no header:

```http
Authorization: Bearer {seu_token}
```

---

## 📌 Resumo das Mudanças

### O que mudou:

1. ✅ **Ingredientes agora têm seu próprio cadastro** em `/api/catalogo/admin/receitas/ingredientes`
2. ✅ **Relacionamento N:N:** Um ingrediente pode estar em várias receitas
3. ✅ **Campo de custo:** Todos os ingredientes têm campo `custo` (obrigatório)
4. ✅ **Novo endpoint:** `/com-ingredientes` retorna receitas com ingredientes incluídos
5. ✅ **Ingredientes dentro de `catalogo/receitas/`:** Toda lógica de ingredientes está centralizada

### O que permanece:

- Endpoints de receitas continuam funcionando
- Endpoint legado `/api/cadastros/admin/receitas/{cod}/ingredientes` mantido para compatibilidade
- Relacionamento com adicionais continua igual

---

## 🎯 Dicas de Performance

1. **Use `/com-ingredientes`** quando precisar dos dados completos de uma vez
2. **Liste ingredientes separadamente** apenas quando necessário filtrar ou paginar
3. **Cache no frontend** os ingredientes que são usados frequentemente
4. **Evite múltiplas chamadas** - prefira endpoints que retornam dados agregados

---

## ❓ FAQ

**P: Posso deletar um ingrediente que está em uma receita?**  
R: Não. Você precisa primeiro remover o ingrediente de todas as receitas antes de deletá-lo.

**P: Posso usar o mesmo ingrediente em várias receitas?**  
R: Sim! Esse é o relacionamento N:N - um ingrediente pode estar em quantas receitas você quiser.

**P: Como calcular o custo total de uma receita?**  
R: Some os custos dos ingredientes multiplicados pelas quantidades: `Σ(ingrediente_custo * quantidade)`

**P: Qual a diferença entre `/receitas/` e `/receitas/com-ingredientes`?**  
R: O primeiro retorna apenas dados da receita. O segundo retorna receita + todos os ingredientes com dados completos em uma única chamada.

**P: O que acontece se eu deletar uma receita?**  
R: Todos os ingredientes e adicionais vinculados são removidos automaticamente (cascade delete).

---

**Última atualização:** 2025-01-18

