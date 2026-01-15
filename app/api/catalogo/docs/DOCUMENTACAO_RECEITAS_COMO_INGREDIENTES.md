# Documentação: Receitas como Ingredientes

## Visão Geral

Agora é possível vincular receitas a outras receitas como se fossem ingredientes. Isso permite criar receitas compostas, onde uma receita pode conter tanto ingredientes básicos quanto outras receitas (sub-receitas).

## Resumo Rápido

### Endpoints Principais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/catalogo/admin/receitas/ingredientes` | Adiciona ingrediente básico ou sub-receita |
| GET | `/api/catalogo/admin/receitas/{receita_id}/ingredientes` | Lista ingredientes de uma receita |
| GET | `/api/catalogo/admin/receitas/com-ingredientes` | Lista receitas com ingredientes detalhados |
| PUT | `/api/catalogo/admin/receitas/ingredientes/{id}` | Atualiza quantidade de um ingrediente |
| DELETE | `/api/catalogo/admin/receitas/ingredientes/{id}` | Remove ingrediente de uma receita |

### Tipos de Ingredientes

- **Ingrediente Básico**: Use `ingrediente_id` no request
- **Sub-receita**: Use `receita_ingrediente_id` no request
- **Importante**: Forneça exatamente um dos dois campos, nunca ambos

## Conceitos

### Tipos de Ingredientes

Uma receita pode ter dois tipos de ingredientes:

1. **Ingrediente Básico**: Um ingrediente cadastrado na tabela de ingredientes (ex: farinha, açúcar, sal)
2. **Sub-receita**: Uma receita completa que é usada como ingrediente de outra receita (ex: massa de pizza usada na receita de pizza completa)

### Exemplo Prático

Imagine uma receita de "Pizza Margherita" que precisa de:
- Ingredientes básicos: farinha, água, sal, azeite
- Sub-receita: "Massa de Pizza" (que por sua vez contém farinha, água, fermento, etc.)

## Autenticação

Todos os endpoints requerem autenticação de administrador. Inclua o token de autenticação no header:

```
Authorization: Bearer <seu_token>
```

## Endpoints da API

### 1. Adicionar Ingrediente ou Sub-receita a uma Receita

**POST** `/api/catalogo/admin/receitas/ingredientes`

Adiciona um ingrediente básico ou uma sub-receita a uma receita.

**Autenticação**: Requer autenticação de administrador

#### Request Body

Você deve fornecer **exatamente um** dos seguintes campos:

**Opção 1: Ingrediente Básico**
```json
{
  "receita_id": 1,
  "ingrediente_id": 5,
  "quantidade": 2.0
}
```

**Opção 2: Sub-receita**
```json
{
  "receita_id": 1,
  "receita_ingrediente_id": 3,
  "quantidade": 1.5
}
```

#### Campos

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|------------|-----------|
| `receita_id` | integer | Sim | ID da receita que receberá o ingrediente |
| `ingrediente_id` | integer | Condicional* | ID do ingrediente básico |
| `receita_ingrediente_id` | integer | Condicional* | ID da receita usada como ingrediente |
| `quantidade` | float | Não | Quantidade do ingrediente/sub-receita |

\* **Importante**: Você deve fornecer exatamente um dos campos (`ingrediente_id` OU `receita_ingrediente_id`), nunca ambos e nunca nenhum.

#### Resposta de Sucesso (201)

```json
{
  "id": 10,
  "receita_id": 1,
  "ingrediente_id": 5,
  "receita_ingrediente_id": null,
  "quantidade": 2.0
}
```

Ou para sub-receita:

```json
{
  "id": 11,
  "receita_id": 1,
  "ingrediente_id": null,
  "receita_ingrediente_id": 3,
  "quantidade": 1.5
}
```

#### Erros Possíveis

- **400 Bad Request**: 
  - "Deve fornecer ingrediente_id ou receita_ingrediente_id"
  - "Deve fornecer apenas um: ingrediente_id ou receita_ingrediente_id"
  - "Ingrediente já cadastrado nesta receita"
  - "Sub-receita já cadastrada nesta receita"
  - "Uma receita não pode ser ingrediente de si mesma"

- **404 Not Found**:
  - "Receita não encontrada"
  - "Ingrediente não encontrado"
  - "Receita ingrediente não encontrada"

---

### 2. Listar Ingredientes de uma Receita

**GET** `/api/catalogo/admin/receitas/{receita_id}/ingredientes`

Retorna todos os ingredientes (básicos e sub-receitas) de uma receita.

**Autenticação**: Requer autenticação de administrador

#### Resposta de Sucesso (200)

```json
[
  {
    "id": 10,
    "receita_id": 1,
    "ingrediente_id": 5,
    "receita_ingrediente_id": null,
    "quantidade": 2.0,
    "ingrediente": {
      "id": 5,
      "nome": "Farinha",
      "descricao": "Farinha de trigo",
      "unidade_medida": "KG",
      "custo": 5.50
    },
    "receita_ingrediente": null
  },
  {
    "id": 11,
    "receita_id": 1,
    "ingrediente_id": null,
    "receita_ingrediente_id": 3,
    "quantidade": 1.5,
    "ingrediente": null,
    "receita_ingrediente": {
      "id": 3,
      "nome": "Massa de Pizza",
      "descricao": "Massa base para pizza",
      "preco_venda": 15.00
    }
  }
]
```

---

### 3. Listar Receitas com Ingredientes Detalhados

**GET** `/api/catalogo/admin/receitas/com-ingredientes`

Retorna receitas com seus ingredientes incluídos, com informações detalhadas.

**Autenticação**: Requer autenticação de administrador

#### Query Parameters

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `empresa_id` | integer | Não | Filtrar por empresa |
| `ativo` | boolean | Não | Filtrar apenas receitas ativas |
| `search` | string | Não | Busca textual por nome/descrição |

#### Resposta de Sucesso (200)

```json
[
  {
    "id": 1,
    "empresa_id": 1,
    "nome": "Pizza Margherita",
    "descricao": "Pizza tradicional italiana",
    "preco_venda": 25.00,
    "custo_total": 8.50,
    "imagem": "https://example.com/pizza.jpg",
    "ativo": true,
    "disponivel": true,
    "created_at": "2026-01-11T10:00:00Z",
    "updated_at": "2026-01-11T10:00:00Z",
    "ingredientes": [
      {
        "id": 10,
        "receita_id": 1,
        "ingrediente_id": 5,
        "receita_ingrediente_id": null,
        "quantidade": 2.0,
        "ingrediente_nome": "Farinha",
        "ingrediente_descricao": "Farinha de trigo",
        "ingrediente_unidade_medida": "KG",
        "ingrediente_custo": 5.50,
        "receita_ingrediente_nome": null,
        "receita_ingrediente_descricao": null,
        "receita_ingrediente_preco_venda": null
      },
      {
        "id": 11,
        "receita_id": 1,
        "ingrediente_id": null,
        "receita_ingrediente_id": 3,
        "quantidade": 1.5,
        "ingrediente_nome": null,
        "ingrediente_descricao": null,
        "ingrediente_unidade_medida": null,
        "ingrediente_custo": null,
        "receita_ingrediente_nome": "Massa de Pizza",
        "receita_ingrediente_descricao": "Massa base para pizza",
        "receita_ingrediente_preco_venda": 15.00
      }
    ]
  }
]
```

#### Como Identificar o Tipo de Ingrediente

Para identificar se um ingrediente é básico ou sub-receita, verifique:

- **Ingrediente Básico**: `ingrediente_id` não é `null` e `receita_ingrediente_id` é `null`
- **Sub-receita**: `ingrediente_id` é `null` e `receita_ingrediente_id` não é `null`

---

### 4. Atualizar Quantidade de um Ingrediente

**PUT** `/api/catalogo/admin/receitas/ingredientes/{receita_ingrediente_id}`

Atualiza a quantidade de um ingrediente ou sub-receita.

**Autenticação**: Requer autenticação de administrador

#### Request Body

```json
{
  "quantidade": 3.0
}
```

#### Resposta de Sucesso (200)

```json
{
  "id": 10,
  "receita_id": 1,
  "ingrediente_id": 5,
  "receita_ingrediente_id": null,
  "quantidade": 3.0
}
```

---

### 5. Remover Ingrediente de uma Receita

**DELETE** `/api/catalogo/admin/receitas/ingredientes/{receita_ingrediente_id}`

Remove um ingrediente ou sub-receita de uma receita.

**Autenticação**: Requer autenticação de administrador

#### Resposta de Sucesso (204 No Content)

---

## Exemplos de Uso no Frontend

### Exemplo 1: Adicionar Ingrediente Básico

```typescript
async function adicionarIngredienteBasico(receitaId: number, ingredienteId: number, quantidade: number) {
  const token = localStorage.getItem('auth_token'); // ou sua forma de obter o token
  
  const response = await fetch(`/api/catalogo/admin/receitas/ingredientes`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      receita_id: receitaId,
      ingrediente_id: ingredienteId,
      quantidade: quantidade
    })
  });
  
  if (!response.ok) {
    throw new Error('Erro ao adicionar ingrediente');
  }
  
  return await response.json();
}
```

### Exemplo 2: Adicionar Sub-receita

```typescript
async function adicionarSubReceita(receitaId: number, subReceitaId: number, quantidade: number) {
  const token = localStorage.getItem('auth_token'); // ou sua forma de obter o token
  
  const response = await fetch(`/api/catalogo/admin/receitas/ingredientes`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      receita_id: receitaId,
      receita_ingrediente_id: subReceitaId,
      quantidade: quantidade
    })
  });
  
  if (!response.ok) {
    throw new Error('Erro ao adicionar sub-receita');
  }
  
  return await response.json();
}
```

### Exemplo 3: Listar e Exibir Ingredientes

```typescript
interface IngredienteDetalhado {
  id: number;
  receita_id: number;
  ingrediente_id: number | null;
  receita_ingrediente_id: number | null;
  quantidade: number | null;
  ingrediente_nome: string | null;
  ingrediente_descricao: string | null;
  ingrediente_unidade_medida: string | null;
  ingrediente_custo: number | null;
  receita_ingrediente_nome: string | null;
  receita_ingrediente_descricao: string | null;
  receita_ingrediente_preco_venda: number | null;
}

function renderizarIngrediente(ingrediente: IngredienteDetalhado) {
  // Verifica se é ingrediente básico ou sub-receita
  if (ingrediente.ingrediente_id !== null) {
    // É um ingrediente básico
    return (
      <div>
        <h4>{ingrediente.ingrediente_nome}</h4>
        <p>{ingrediente.ingrediente_descricao}</p>
        <p>Quantidade: {ingrediente.quantidade} {ingrediente.ingrediente_unidade_medida}</p>
        <p>Custo: R$ {ingrediente.ingrediente_custo}</p>
      </div>
    );
  } else if (ingrediente.receita_ingrediente_id !== null) {
    // É uma sub-receita
    return (
      <div>
        <h4>📋 {ingrediente.receita_ingrediente_nome}</h4>
        <p>{ingrediente.receita_ingrediente_descricao}</p>
        <p>Quantidade: {ingrediente.quantidade} unidade(s)</p>
        <p>Preço de venda: R$ {ingrediente.receita_ingrediente_preco_venda}</p>
        <small>Sub-receita (receita completa usada como ingrediente)</small>
      </div>
    );
  }
}
```

### Exemplo 4: Formulário para Adicionar Ingrediente

```typescript
function FormularioAdicionarIngrediente({ receitaId }: { receitaId: number }) {
  const [tipo, setTipo] = useState<'ingrediente' | 'subreceita'>('ingrediente');
  const [ingredienteId, setIngredienteId] = useState<number | null>(null);
  const [subReceitaId, setSubReceitaId] = useState<number | null>(null);
  const [quantidade, setQuantidade] = useState<number>(1);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const body = {
      receita_id: receitaId,
      quantidade: quantidade
    };
    
    if (tipo === 'ingrediente') {
      if (!ingredienteId) {
        alert('Selecione um ingrediente');
        return;
      }
      body.ingrediente_id = ingredienteId;
    } else {
      if (!subReceitaId) {
        alert('Selecione uma sub-receita');
        return;
      }
      body.receita_ingrediente_id = subReceitaId;
    }
    
    try {
      await adicionarIngredienteBasico(receitaId, ingredienteId!, quantidade);
      // ou await adicionarSubReceita(receitaId, subReceitaId!, quantidade);
      alert('Ingrediente adicionado com sucesso!');
    } catch (error) {
      alert('Erro ao adicionar ingrediente');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>
          Tipo:
          <select value={tipo} onChange={(e) => setTipo(e.target.value as 'ingrediente' | 'subreceita')}>
            <option value="ingrediente">Ingrediente Básico</option>
            <option value="subreceita">Sub-receita</option>
          </select>
        </label>
      </div>
      
      {tipo === 'ingrediente' ? (
        <div>
          <label>
            Ingrediente:
            <select value={ingredienteId || ''} onChange={(e) => setIngredienteId(Number(e.target.value))}>
              <option value="">Selecione um ingrediente</option>
              {/* Lista de ingredientes */}
            </select>
          </label>
        </div>
      ) : (
        <div>
          <label>
            Sub-receita:
            <select value={subReceitaId || ''} onChange={(e) => setSubReceitaId(Number(e.target.value))}>
              <option value="">Selecione uma receita</option>
              {/* Lista de receitas disponíveis */}
            </select>
          </label>
        </div>
      )}
      
      <div>
        <label>
          Quantidade:
          <input 
            type="number" 
            step="0.01" 
            value={quantidade} 
            onChange={(e) => setQuantidade(Number(e.target.value))}
          />
        </label>
      </div>
      
      <button type="submit">Adicionar</button>
    </form>
  );
}
```

## Validações Importantes

### 1. Validação de Campos Mutuamente Exclusivos

O frontend deve garantir que:
- Se `ingrediente_id` for fornecido, `receita_ingrediente_id` deve ser `null` ou não enviado
- Se `receita_ingrediente_id` for fornecido, `ingrediente_id` deve ser `null` ou não enviado
- Pelo menos um dos dois campos deve ser fornecido

### 2. Validação de Referência Circular

O backend já valida que uma receita não pode ser ingrediente de si mesma, mas o frontend pode prevenir isso mostrando um aviso antes de enviar.

### 3. Validação de Duplicatas

O backend retorna erro 400 se tentar adicionar o mesmo ingrediente/sub-receita duas vezes na mesma receita. O frontend pode verificar isso antes de enviar.

## Cálculo de Custo

O campo `custo_total` da receita é calculado automaticamente considerando:
- Custo dos ingredientes básicos: `quantidade × custo_ingrediente`
- Custo das sub-receitas: `quantidade × custo_total_da_sub_receita` (calculado recursivamente)

O cálculo é feito automaticamente pelo backend e não precisa ser implementado no frontend.

## Notas Técnicas

1. **Proteção contra Loops Infinitos**: O sistema previne referências circulares (ex: receita A usa receita B, receita B usa receita A). Se detectar um loop, retorna custo 0 para evitar cálculo infinito.

2. **Performance**: O cálculo de custo de receitas com muitas sub-receitas aninhadas pode ser mais lento. Considere cachear os resultados no frontend se necessário.

3. **Cascata de Exclusão**: Se uma receita for deletada, todos os seus ingredientes (básicos e sub-receitas) são removidos automaticamente. Se uma sub-receita for deletada, ela é removida de todas as receitas que a utilizam.

## Suporte

Para dúvidas ou problemas, consulte a documentação da API ou entre em contato com a equipe de backend.
