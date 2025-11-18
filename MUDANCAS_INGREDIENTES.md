# Mudanças na Estrutura de Ingredientes

## Resumo das Alterações

Todas as funcionalidades relacionadas a **Ingredientes** foram movidas para dentro de `catalogo/receitas/`, incluindo models, repositories, services, schemas e routers.

## Principais Mudanças

### 1. Estrutura de Arquivos

**ANTES:**
```
app/api/cadastros/
  ├── models/model_ingrediente.py
  ├── repositories/repo_ingrediente.py
  ├── services/service_ingrediente.py
  ├── schemas/schema_ingrediente.py
  └── router/admin/router_ingredientes.py
```

**DEPOIS:**
```
app/api/catalogo/receitas/
  ├── models/model_ingrediente.py
  ├── repositories/repo_ingrediente.py
  ├── services/service_ingrediente.py
  ├── schemas/schema_ingrediente.py
  └── router/router_ingredientes.py
```

### 2. Relacionamento Ingrediente ↔ Receita

**MUDANÇA CRÍTICA:** O relacionamento mudou de **1:1** para **N:N** (Muitos para Muitos).

- ✅ **Um ingrediente** pode estar em **várias receitas**
- ✅ **Uma receita** pode ter **vários ingredientes**
- ❌ Removida a restrição que impedia um ingrediente de pertencer a múltiplas receitas

### 3. Schema do Banco de Dados

O modelo `IngredienteModel` agora está no schema `catalogo` (não mais em `cadastros`):

```python
__tablename__ = "ingredientes"
__table_args__ = ({"schema": "catalogo"},)
```

### 4. Novo Campo: Custo

Todos os ingredientes agora possuem um campo **`custo`** (Numeric(18, 2)):

```python
custo = Column(Numeric(18, 2), nullable=False, default=0)
```

Este campo é obrigatório e deve ser enviado ao criar/atualizar um ingrediente.

### 5. Rotas Atualizadas

#### Nova Rota Base
**ANTES:** `/api/cadastros/admin/ingredientes`  
**DEPOIS:** `/api/catalogo/admin/receitas/ingredientes`

Todas as rotas de ingredientes agora estão aninhadas dentro de receitas:

- `GET /api/catalogo/admin/receitas/ingredientes/` - Listar ingredientes
- `POST /api/catalogo/admin/receitas/ingredientes/` - Criar ingrediente
- `GET /api/catalogo/admin/receitas/ingredientes/{ingrediente_id}` - Buscar ingrediente
- `PUT /api/catalogo/admin/receitas/ingredientes/{ingrediente_id}` - Atualizar ingrediente
- `DELETE /api/catalogo/admin/receitas/ingredientes/{ingrediente_id}` - Deletar ingrediente

## Schemas Atualizados

### CriarIngredienteRequest
```typescript
{
  empresa_id: number;
  nome: string; // min 1, max 100 caracteres
  descricao?: string; // max 255 caracteres (opcional)
  unidade_medida?: string; // ex: "KG", "L", "UN", "GR" (opcional)
  custo: number; // OBRIGATÓRIO - decimal(18,2), padrão: 0
  ativo?: boolean; // padrão: true
}
```

### AtualizarIngredienteRequest
```typescript
{
  nome?: string; // min 1, max 100 caracteres (opcional)
  descricao?: string; // max 255 caracteres (opcional)
  unidade_medida?: string; // ex: "KG", "L", "UN", "GR" (opcional)
  custo?: number; // decimal(18,2) (opcional)
  ativo?: boolean; // (opcional)
}
```

### IngredienteResponse
```typescript
{
  id: number;
  empresa_id: number;
  nome: string;
  descricao?: string;
  unidade_medida?: string;
  custo: number; // decimal(18,2)
  ativo: boolean;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}
```

## Regras de Negócio Atualizadas

### 1. Criação de Ingrediente
- ✅ `custo` é obrigatório (padrão: 0 se não informado)
- ✅ `empresa_id` deve existir
- ✅ `nome` deve ser único por empresa (validação recomendada no frontend)

### 2. Atualização de Ingrediente
- ✅ Pode atualizar qualquer campo (parcialmente)
- ✅ `custo` pode ser atualizado independentemente

### 3. Exclusão de Ingrediente
- ⚠️ **NÃO é possível deletar** um ingrediente que está vinculado a **uma ou mais receitas**
- ✅ Para deletar, primeiro remova o ingrediente de todas as receitas
- ❌ Erro 400 se tentar deletar ingrediente vinculado

### 4. Vinculação Ingrediente ↔ Receita

**ANTES:** 
- ❌ Um ingrediente só podia estar em 1 receita
- ❌ Tentar vincular a segunda receita gerava erro 400

**DEPOIS:**
- ✅ Um ingrediente pode estar em várias receitas
- ✅ Pode adicionar o mesmo ingrediente em múltiplas receitas
- ❌ Não pode adicionar o mesmo ingrediente **duas vezes** na **mesma receita** (duplicata)

## Imports Atualizados (para referência backend)

```python
# Model
from app.api.catalogo.receitas.models.model_ingrediente import IngredienteModel

# Repository
from app.api.catalogo.receitas.repositories.repo_ingrediente import IngredienteRepository

# Service
from app.api.catalogo.receitas.services.service_ingrediente import IngredienteService

# Schemas
from app.api.catalogo.receitas.schemas.schema_ingrediente import (
    CriarIngredienteRequest,
    AtualizarIngredienteRequest,
    IngredienteResponse,
)
```

## Checklist para Implementação no Frontend

- [ ] Atualizar todas as chamadas de API de `/api/cadastros/admin/ingredientes` para `/api/catalogo/admin/receitas/ingredientes`
- [ ] Adicionar campo `custo` (obrigatório) nos formulários de criar/editar ingrediente
- [ ] Atualizar validações para permitir que um ingrediente apareça em múltiplas receitas
- [ ] Remover validação que impedia reutilização de ingredientes
- [ ] Adicionar mensagem de erro ao tentar deletar ingrediente vinculado a receitas
- [ ] Atualizar listagens e cards de ingredientes para exibir o custo
- [ ] Atualizar imports/types/interfaces conforme novos schemas

## Exemplo de Requisição

### Criar Ingrediente
```http
POST /api/catalogo/admin/receitas/ingredientes/
Content-Type: application/json
Authorization: Bearer {token}

{
  "empresa_id": 1,
  "nome": "Farinha de Trigo",
  "descricao": "Farinha de trigo tipo 1",
  "unidade_medida": "KG",
  "custo": 5.50,
  "ativo": true
}
```

### Listar Ingredientes
```http
GET /api/catalogo/admin/receitas/ingredientes/?empresa_id=1&apenas_ativos=true
Authorization: Bearer {token}
```

### Adicionar Ingrediente a Receita
```http
POST /api/catalogo/admin/receitas/ingredientes
Content-Type: application/json
Authorization: Bearer {token}

{
  "receita_id": 10,
  "ingrediente_id": 5,
  "quantidade": 2.5
}
```

**Nota:** Agora é possível adicionar o ingrediente ID 5 a múltiplas receitas diferentes, desde que não seja duplicado na mesma receita.

