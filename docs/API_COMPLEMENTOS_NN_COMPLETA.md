# 📚 Documentação Completa - Sistema de Complementos N:N

## 🎯 Visão Geral

O sistema de **Complementos** utiliza um relacionamento **N:N (Muitos para Muitos)** entre **Complementos** e **Itens de Complemento**.

### Conceitos Principais

- **Complemento**: Grupo de itens com configurações (ex: "Molhos", "Tamanhos", "Extras")
- **Item de Complemento**: Item individual que pode pertencer a vários complementos (ex: "Ketchup", "Grande")
- **Relacionamento N:N**: Um item pode estar em vários complementos e um complemento pode ter vários itens

### Vantagens do Relacionamento N:N

✅ **Reutilização**: Criar "Ketchup" uma vez, usar em vários complementos  
✅ **Flexibilidade**: Adicionar item existente a novo complemento sem duplicar  
✅ **Manutenção**: Atualizar item uma vez, reflete em todos os complementos  
✅ **Organização**: Itens são entidades independentes, vínculos são gerenciados separadamente

---

## 🗄️ Estrutura do Banco de Dados

### Tabelas

#### 1. `complemento_produto` (Complementos)
```sql
CREATE TABLE catalogo.complemento_produto (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL,
    nome VARCHAR(100) NOT NULL,
    descricao VARCHAR(255),
    obrigatorio BOOLEAN DEFAULT FALSE,
    quantitativo BOOLEAN DEFAULT FALSE,
    permite_multipla_escolha BOOLEAN DEFAULT TRUE,
    ativo BOOLEAN DEFAULT TRUE,
    ordem INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 2. `complemento_itens` (Itens)
```sql
CREATE TABLE catalogo.complemento_itens (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL,
    nome VARCHAR(100) NOT NULL,
    descricao VARCHAR(255),
    preco NUMERIC(18,2) DEFAULT 0,
    custo NUMERIC(18,2) DEFAULT 0,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 3. `complemento_item_link` (Tabela de Associação N:N)
```sql
CREATE TABLE catalogo.complemento_item_link (
    complemento_id INTEGER NOT NULL REFERENCES catalogo.complemento_produto(id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES catalogo.complemento_itens(id) ON DELETE CASCADE,
    ordem INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (complemento_id, item_id)
);
```

---

## 🔧 Endpoints da API

### Base URL
**Admin**: `/api/catalogo/admin/complementos`

### Endpoints - Itens (Independentes)

#### 1. Criar Item
```http
POST /api/catalogo/admin/complementos/itens/
```

**Request:**
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

#### 2. Listar Itens
```http
GET /api/catalogo/admin/complementos/itens/?empresa_id=1&apenas_ativos=true
```

#### 3. Buscar Item
```http
GET /api/catalogo/admin/complementos/itens/{item_id}
```

#### 4. Atualizar Item
```http
PUT /api/catalogo/admin/complementos/itens/{item_id}
```

#### 5. Deletar Item
```http
DELETE /api/catalogo/admin/complementos/itens/{item_id}
```

### Endpoints - Vincular Itens a Complementos

#### 6. Vincular Itens a um Complemento
```http
POST /api/catalogo/admin/complementos/{complemento_id}/itens/vincular
```

**Request:**
```json
{
  "item_ids": [1, 2, 3],
  "ordens": [0, 1, 2]
}
```

**Response:**
```json
{
  "complemento_id": 1,
  "itens_vinculados": [
    {
      "id": 1,
      "nome": "Ketchup",
      "preco": 0.0,
      "ordem": 0
    },
    {
      "id": 2,
      "nome": "Maionese",
      "preco": 0.0,
      "ordem": 1
    }
  ],
  "message": "Itens vinculados com sucesso"
}
```

#### 7. Desvincular Item de um Complemento
```http
DELETE /api/catalogo/admin/complementos/{complemento_id}/itens/{item_id}
```

#### 8. Listar Itens de um Complemento
```http
GET /api/catalogo/admin/complementos/{complemento_id}/itens?apenas_ativos=true
```

#### 9. Atualizar Ordem dos Itens
```http
PUT /api/catalogo/admin/complementos/{complemento_id}/itens/ordem
```

**Request:**
```json
{
  "item_ordens": [
    { "item_id": 1, "ordem": 0 },
    { "item_id": 2, "ordem": 1 },
    { "item_id": 3, "ordem": 2 }
  ]
}
```

**Nota**: O campo `item_ordens` é uma lista de objetos com `item_id` e `ordem`.

---

## 💡 Fluxo de Uso Completo

### Passo 1: Criar Itens (Independentes)

```typescript
// Criar item "Ketchup"
const ketchup = await fetch('/api/catalogo/admin/complementos/itens/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    empresa_id: 1,
    nome: "Ketchup",
    preco: 0.0,
    ativo: true
  })
});

const ketchupData = await ketchup.json();
const ketchupId = ketchupData.id; // Ex: 1

// Criar item "Maionese"
const maionese = await fetch('/api/catalogo/admin/complementos/itens/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    empresa_id: 1,
    nome: "Maionese",
    preco: 0.0,
    ativo: true
  })
});

const maioneseData = await maionese.json();
const maioneseId = maioneseData.id; // Ex: 2
```

### Passo 2: Criar Complementos

```typescript
// Criar complemento "Molhos"
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
const molhosId = molhosData.id; // Ex: 1
```

### Passo 3: Vincular Itens aos Complementos

```typescript
// Vincular Ketchup e Maionese ao complemento "Molhos"
await fetch(`/api/catalogo/admin/complementos/${molhosId}/itens/vincular`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    item_ids: [ketchupId, maioneseId],
    ordens: [0, 1]
  })
});
```

### Passo 4: Reutilizar Item em Outro Complemento

```typescript
// Criar complemento "Extras"
const extras = await fetch('/api/catalogo/admin/complementos/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    empresa_id: 1,
    nome: "Extras",
    obrigatorio: false,
    permite_multipla_escolha: true
  })
});

const extrasData = await extras.json();
const extrasId = extrasData.id; // Ex: 2

// Vincular o mesmo "Ketchup" ao complemento "Extras" (reutilização!)
await fetch(`/api/catalogo/admin/complementos/${extrasId}/itens/vincular`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    item_ids: [ketchupId], // Mesmo item!
    ordens: [0]
  })
});
```

---

## 📊 Exemplo Visual

```
Complemento "Molhos" (id: 1)
├── Ketchup (id: 1, preco: R$ 0,00) ← ordem: 0
└── Maionese (id: 2, preco: R$ 0,00) ← ordem: 1

Complemento "Extras" (id: 2)
├── Ketchup (id: 1, preco: R$ 0,00) ← Reutilizado! ordem: 0
└── Bacon (id: 3, preco: R$ 3,00) ← ordem: 1
```

**Resultado**: O item "Ketchup" está em 2 complementos diferentes, mas é o mesmo item no banco!

---

## ⚠️ Regras de Negócio

1. **Empresa**: Itens e complementos devem pertencer à mesma empresa
2. **Deleção em Cascata**: 
   - Deletar complemento remove apenas os vínculos (não deleta os itens)
   - Deletar item remove o item de todos os complementos
3. **Ordem**: A ordem é específica por complemento (mesmo item pode ter ordens diferentes em complementos diferentes)
4. **Validação**: Um item só pode ser vinculado uma vez ao mesmo complemento

---

## 🔍 Queries Úteis

### SQL: Listar Itens de um Complemento
```sql
SELECT 
    i.id,
    i.nome,
    i.preco,
    i.ativo,
    l.ordem
FROM catalogo.complemento_itens i
INNER JOIN catalogo.complemento_item_link l ON i.id = l.item_id
WHERE l.complemento_id = 1
  AND i.ativo = true
ORDER BY l.ordem;
```

### SQL: Listar Complementos de um Item
```sql
SELECT 
    c.id,
    c.nome,
    c.obrigatorio,
    l.ordem
FROM catalogo.complemento_produto c
INNER JOIN catalogo.complemento_item_link l ON c.id = l.complemento_id
WHERE l.item_id = 1
  AND c.ativo = true
ORDER BY l.ordem;
```

---

## 📝 Schemas TypeScript

```typescript
interface CriarItemRequest {
  empresa_id: number;
  nome: string;
  descricao?: string;
  preco: number;
  custo: number;
  ativo?: boolean;
}

interface VincularItensComplementoRequest {
  item_ids: number[];
  ordens?: number[];
}

interface AtualizarOrdemItensRequest {
  item_ordens: Array<{
    item_id: number;
    ordem: number;
  }>;
}
```

---

## 🎯 Resumo dos Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/itens/` | Criar item independente |
| GET | `/itens/` | Listar itens |
| GET | `/itens/{id}` | Buscar item |
| PUT | `/itens/{id}` | Atualizar item |
| DELETE | `/itens/{id}` | Deletar item |
| POST | `/{complemento_id}/itens/vincular` | Vincular itens |
| DELETE | `/{complemento_id}/itens/{item_id}` | Desvincular item |
| GET | `/{complemento_id}/itens` | Listar itens do complemento |
| PUT | `/{complemento_id}/itens/ordem` | Atualizar ordem |

---

## 📞 Suporte

Para mais informações, consulte:
- `docs/API_COMPLEMENTOS_FRONTEND.md` - Documentação completa
- `docs/API_COMPLEMENTOS_DIAGRAMA.md` - Diagramas visuais
- `docs/API_COMPLEMENTOS_RESUMO.md` - Resumo rápido

