# 📚 Documentação: Sistema de Receitas e Ingredientes

## 🎯 Visão Geral

O sistema de **Receitas e Ingredientes** é composto por três entidades principais:

1. **Ingredientes** - Cadastro independente de ingredientes
2. **Receitas** - Receitas que utilizam ingredientes
3. **Adicionais** - Produtos adicionais que podem ser vinculados a receitas

### ⚠️ Regra Fundamental: Relacionamento 1:1

**UM ingrediente só pode pertencer a UMA receita.** Esta é a regra mais importante do sistema:
- Um ingrediente cadastrado pode estar vinculado a apenas uma receita
- Se tentar vincular um ingrediente já vinculado a outra receita, retornará erro 400
- Para usar o mesmo ingrediente em outra receita, é necessário cadastrar um novo ingrediente

---

## 📊 Modelos de Dados (Models)

### 1. IngredienteModel (`catalogo.ingredientes`)

Tabela independente para cadastro de ingredientes.

```python
{
    id: int                          # PK, auto-incremento
    empresa_id: int                  # ID da empresa (sem FK explícita)
    nome: string(100)                # Nome do ingrediente (ex: "Farinha", "Açúcar")
    descricao: string(255)           # Descrição opcional
    unidade_medida: string(10)       # Unidade (ex: "KG", "L", "UN", "GR")
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

Tabela de relacionamento **1:1** entre receitas e ingredientes.

```python
{
    id: int                          # PK, auto-incremento
    receita_id: int                  # FK: catalogo.receitas.id
    ingrediente_id: int              # FK: catalogo.ingredientes.id (UNIQUE)
    quantidade: decimal(18,4)        # Quantidade do ingrediente
}
```

**Constraint UNIQUE em `ingrediente_id`** garante que um ingrediente só pode estar em uma receita.

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
  └── Ingrediente (1:N) - Um ingrediente pertence a uma empresa
  └── Receita (1:N) - Uma receita pertence a uma empresa

Receita (1) ────< (1) Ingrediente
  └── ReceitaIngredienteModel (tabela de relacionamento 1:1)

Receita (1) ────< (N) ReceitaAdicionalModel >─── (1) Produto
```

---

## 📝 Schemas (Request/Response)

### Ingredientes

#### CriarIngredienteRequest (POST)
```json
{
    "empresa_id": 1,
    "nome": "Farinha de Trigo",
    "descricao": "Farinha branca premium",
    "unidade_medida": "KG",
    "ativo": true
}
```

#### AtualizarIngredienteRequest (PUT)
```json
{
    "nome": "Farinha de Trigo",
    "descricao": "Farinha branca premium atualizada",
    "unidade_medida": "KG",
    "ativo": true
}
```
*Todos os campos são opcionais.*

#### IngredienteResponse
```json
{
    "id": 1,
    "empresa_id": 1,
    "nome": "Farinha de Trigo",
    "descricao": "Farinha branca premium",
    "unidade_medida": "KG",
    "ativo": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

### Receitas

#### ReceitaIn (POST)
```json
{
    "empresa_id": 1,
    "nome": "Pizza Margherita",
    "descricao": "Pizza clássica italiana",
    "preco_venda": "25.99",
    "imagem": "https://exemplo.com/pizza.jpg",
    "ativo": true,
    "disponivel": true
}
```

#### ReceitaUpdate (PUT)
```json
{
    "nome": "Pizza Margherita Premium",
    "preco_venda": "29.99",
    "ativo": true
}
```
*Todos os campos são opcionais.*

#### ReceitaOut
```json
{
    "id": 1,
    "empresa_id": 1,
    "nome": "Pizza Margherita",
    "descricao": "Pizza clássica italiana",
    "preco_venda": "25.99",
    "imagem": "https://exemplo.com/pizza.jpg",
    "ativo": true,
    "disponivel": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

### Vinculação Ingrediente-Receita

#### ReceitaIngredienteIn (POST)
```json
{
    "receita_id": 1,
    "ingrediente_id": 5,
    "quantidade": 0.5
}
```

**⚠️ IMPORTANTE:** Se `ingrediente_id: 5` já estiver vinculado a outra receita, retornará:
```json
{
    "detail": "Ingrediente já está vinculado à receita ID 3. Um ingrediente só pode pertencer a uma receita."
}
```

#### ReceitaIngredienteOut
```json
{
    "id": 10,
    "receita_id": 1,
    "ingrediente_id": 5,
    "quantidade": 0.5
}
```

### Adicionais de Receita

#### AdicionalIn (POST)
```json
{
    "receita_id": 1,
    "adicional_cod_barras": "7891234567890",
    "preco": "3.50"
}
```

#### AdicionalOut
```json
{
    "id": 1,
    "receita_id": 1,
    "adicional_cod_barras": "7891234567890",
    "preco": "3.50"
}
```

---

## 🛣️ Rotas e Endpoints

### Base URL
```
/api/catalogo/admin
```

**Todas as rotas requerem autenticação JWT** (exceto onde especificado).

---

### 📦 Ingredientes (`/api/catalogo/admin/ingredientes`)

#### 1. Listar Ingredientes
```http
GET /api/catalogo/admin/ingredientes/?empresa_id=1&apenas_ativos=true
```

**Query Params:**
- `empresa_id` (obrigatório): ID da empresa
- `apenas_ativos` (opcional, default: `true`): Filtrar apenas ingredientes ativos

**Response:** `List[IngredienteResponse]`

#### 2. Criar Ingrediente
```http
POST /api/catalogo/admin/ingredientes/
Content-Type: application/json

{
    "empresa_id": 1,
    "nome": "Farinha de Trigo",
    "descricao": "Farinha branca premium",
    "unidade_medida": "KG",
    "ativo": true
}
```

**Response:** `IngredienteResponse` (201 Created)

#### 3. Buscar Ingrediente por ID
```http
GET /api/catalogo/admin/ingredientes/{ingrediente_id}
```

**Response:** `IngredienteResponse`

#### 4. Atualizar Ingrediente
```http
PUT /api/catalogo/admin/ingredientes/{ingrediente_id}
Content-Type: application/json

{
    "nome": "Farinha de Trigo Atualizada",
    "ativo": false
}
```

**Response:** `IngredienteResponse`

#### 5. Deletar Ingrediente
```http
DELETE /api/catalogo/admin/ingredientes/{ingrediente_id}
```

**Regra:** Só é possível deletar se o ingrediente **NÃO** estiver vinculado a nenhuma receita.

**Response:** 
```json
{
    "message": "Ingrediente deletado com sucesso"
}
```

**Erro 400:** Se o ingrediente estiver vinculado a uma receita:
```json
{
    "detail": "Não é possível deletar ingrediente que está vinculado a uma receita"
}
```

---

### 🍕 Receitas (`/api/catalogo/admin/receitas`)

#### 1. Listar Receitas
```http
GET /api/catalogo/admin/receitas/?empresa_id=1&ativo=true
```

**Query Params:**
- `empresa_id` (opcional): Filtrar por empresa
- `ativo` (opcional): Filtrar por status ativo

**Response:** `List[ReceitaOut]`

#### 2. Criar Receita
```http
POST /api/catalogo/admin/receitas/
Content-Type: application/json

{
    "empresa_id": 1,
    "nome": "Pizza Margherita",
    "descricao": "Pizza clássica italiana",
    "preco_venda": "25.99",
    "imagem": "https://exemplo.com/pizza.jpg",
    "ativo": true,
    "disponivel": true
}
```

**Response:** `ReceitaOut` (201 Created)

#### 3. Buscar Receita por ID
```http
GET /api/catalogo/admin/receitas/{receita_id}
```

**Response:** `ReceitaOut`

#### 4. Atualizar Receita
```http
PUT /api/catalogo/admin/receitas/{receita_id}
Content-Type: application/json

{
    "nome": "Pizza Margherita Premium",
    "preco_venda": "29.99"
}
```

**Response:** `ReceitaOut`

#### 5. Deletar Receita
```http
DELETE /api/catalogo/admin/receitas/{receita_id}
```

**Response:** 204 No Content

---

### 🔗 Vincular Ingredientes a Receitas

#### 1. Listar Ingredientes de uma Receita
```http
GET /api/catalogo/admin/receitas/{receita_id}/ingredientes
```

**Response:** `List[ReceitaIngredienteOut]`

#### 2. Adicionar Ingrediente a Receita
```http
POST /api/catalogo/admin/receitas/ingredientes
Content-Type: application/json

{
    "receita_id": 1,
    "ingrediente_id": 5,
    "quantidade": 0.5
}
```

**⚠️ IMPORTANTE:** 
- Se o `ingrediente_id: 5` já estiver vinculado a outra receita, retornará **400 Bad Request**
- Um ingrediente só pode estar em UMA receita

**Response:** `ReceitaIngredienteOut` (201 Created)

**Erro 400:**
```json
{
    "detail": "Ingrediente já está vinculado à receita ID 3. Um ingrediente só pode pertencer a uma receita."
}
```

#### 3. Atualizar Quantidade do Ingrediente na Receita
```http
PUT /api/catalogo/admin/receitas/ingredientes/{receita_ingrediente_id}
Content-Type: application/json

{
    "quantidade": 0.75
}
```

**Nota:** `receita_ingrediente_id` é o ID do vínculo (tabela `receita_ingrediente`), não o ID do ingrediente.

**Response:** `ReceitaIngredienteOut`

#### 4. Remover Ingrediente da Receita
```http
DELETE /api/catalogo/admin/receitas/ingredientes/{receita_ingrediente_id}
```

**Nota:** Isso **desvincula** o ingrediente da receita, mas **NÃO deleta** o ingrediente.

**Response:** 204 No Content

---

### ➕ Adicionais de Receita

#### 1. Listar Adicionais de uma Receita
```http
GET /api/catalogo/admin/receitas/{receita_id}/adicionais
```

**Response:** `List[AdicionalOut]`

#### 2. Adicionar Adicional a Receita
```http
POST /api/catalogo/admin/receitas/adicionais
Content-Type: application/json

{
    "receita_id": 1,
    "adicional_cod_barras": "7891234567890",
    "preco": "3.50"
}
```

**Response:** `AdicionalOut` (201 Created)

#### 3. Atualizar Adicional da Receita
```http
PUT /api/catalogo/admin/receitas/adicionais/{adicional_id}
Content-Type: application/json

{
    "preco": "4.00"
}
```

**Response:** `AdicionalOut`

#### 4. Remover Adicional da Receita
```http
DELETE /api/catalogo/admin/receitas/adicionais/{adicional_id}
```

**Response:** 204 No Content

---

## 🔄 Fluxo de Uso Recomendado

### 1. Criar uma Receita Completa

```javascript
// 1. Criar os ingredientes primeiro
const ingredientes = [
    { empresa_id: 1, nome: "Farinha", unidade_medida: "KG" },
    { empresa_id: 1, nome: "Açúcar", unidade_medida: "KG" },
    { empresa_id: 1, nome: "Ovos", unidade_medida: "UN" }
];

const ingredientesCriados = [];
for (const ing of ingredientes) {
    const response = await fetch('/api/catalogo/admin/ingredientes/', {
        method: 'POST',
        body: JSON.stringify(ing)
    });
    ingredientesCriados.push(await response.json());
}

// 2. Criar a receita
const receita = {
    empresa_id: 1,
    nome: "Bolo de Chocolate",
    descricao: "Bolo delicioso",
    preco_venda: "35.00",
    ativo: true,
    disponivel: true
};

const receitaCriada = await fetch('/api/catalogo/admin/receitas/', {
    method: 'POST',
    body: JSON.stringify(receita)
}).then(r => r.json());

// 3. Vincular ingredientes à receita
for (const ing of ingredientesCriados) {
    await fetch('/api/catalogo/admin/receitas/ingredientes', {
        method: 'POST',
        body: JSON.stringify({
            receita_id: receitaCriada.id,
            ingrediente_id: ing.id,
            quantidade: 0.5  // quantidade específica
        })
    });
}
```

### 2. Tratamento de Erro ao Vincular Ingrediente Já Usado

```javascript
async function adicionarIngredienteAReceita(receitaId, ingredienteId, quantidade) {
    try {
        const response = await fetch('/api/catalogo/admin/receitas/ingredientes', {
            method: 'POST',
            body: JSON.stringify({
                receita_id: receitaId,
                ingrediente_id: ingredienteId,
                quantidade: quantidade
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            if (response.status === 400 && error.detail.includes('já está vinculado')) {
                // Ingrediente já está em outra receita
                alert('Este ingrediente já está sendo usado em outra receita. Crie um novo ingrediente ou remova-o da receita anterior.');
            }
            throw new Error(error.detail);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Erro ao adicionar ingrediente:', error);
        throw error;
    }
}
```

### 3. Validar Antes de Deletar Ingrediente

```javascript
async function deletarIngrediente(ingredienteId) {
    try {
        const response = await fetch(`/api/catalogo/admin/ingredientes/${ingredienteId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const error = await response.json();
            if (response.status === 400 && error.detail.includes('vinculado')) {
                // Primeiro, perguntar qual receita está usando
                alert('Este ingrediente está vinculado a uma receita. Primeiro remova-o da receita antes de deletar.');
                return;
            }
            throw new Error(error.detail);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Erro ao deletar ingrediente:', error);
        throw error;
    }
}
```

---

## ⚠️ Regras de Negócio Importantes

### 1. Relacionamento 1:1 Ingrediente-Receita
- ✅ Um ingrediente só pode estar em UMA receita
- ✅ Para usar o mesmo ingrediente em outra receita, crie um NOVO ingrediente
- ❌ Não é possível vincular um ingrediente já vinculado a outra receita

### 2. Deletar Ingrediente
- ✅ Só é possível deletar se o ingrediente NÃO estiver vinculado a nenhuma receita
- ❌ Se estiver vinculado, deve primeiro desvincular da receita

### 3. Adicionais
- ✅ Um produto (por código de barras) pode ser adicional de múltiplas receitas
- ✅ Diferente de ingredientes, não há restrição de 1:1

---

## 📋 Resumo para Frontend

### Workflow Típico

1. **Cadastrar Ingredientes** → `/api/catalogo/admin/ingredientes/`
2. **Criar Receita** → `/api/catalogo/admin/receitas/`
3. **Vincular Ingredientes** → `/api/catalogo/admin/receitas/ingredientes`
   - ⚠️ Validar se ingrediente já está em outra receita
4. **Gerenciar Receita** → CRUD completo disponível
5. **Listar Receitas com Ingredientes** → 
   - GET `/api/catalogo/admin/receitas/{id}` para receita
   - GET `/api/catalogo/admin/receitas/{id}/ingredientes` para ingredientes

### Validações no Frontend

- ✅ Antes de vincular ingrediente: verificar se já está em outra receita
- ✅ Antes de deletar ingrediente: verificar se está vinculado a alguma receita
- ✅ Ao mostrar ingredientes disponíveis: filtrar os já vinculados (se necessário)

### IDs Importantes

- `ingrediente_id`: ID do ingrediente na tabela `ingredientes`
- `receita_id`: ID da receita na tabela `receitas`
- `receita_ingrediente_id`: ID do vínculo na tabela `receita_ingrediente` (usado em PUT/DELETE de vinculação)

---

## 🔍 Exemplos de Uso Completo

### Exemplo: Criar Receita de Pizza

```javascript
// 1. Criar ingredientes
const farinha = await criarIngrediente({
    empresa_id: 1,
    nome: "Farinha",
    unidade_medida: "KG"
});

const queijo = await criarIngrediente({
    empresa_id: 1,
    nome: "Queijo Mussarela",
    unidade_medida: "KG"
});

// 2. Criar receita
const pizza = await criarReceita({
    empresa_id: 1,
    nome: "Pizza Margherita",
    preco_venda: "25.99",
    ativo: true,
    disponivel: true
});

// 3. Vincular ingredientes
await vincularIngrediente(pizza.id, farinha.id, 0.5);
await vincularIngrediente(pizza.id, queijo.id, 0.3);

// 4. Listar receita completa
const receitaCompleta = await getReceita(pizza.id);
const ingredientesDaReceita = await getIngredientesReceita(pizza.id);
```

---

**Última atualização:** 2024-01-01  
**Versão da API:** 1.0.0

