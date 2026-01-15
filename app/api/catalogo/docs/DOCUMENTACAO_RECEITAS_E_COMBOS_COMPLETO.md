# Documentação: Receitas e Combos - Sistema Completo de Vinculação

## Visão Geral

O sistema agora permite vincular diferentes tipos de itens de forma flexível:

### Receitas podem conter:
- ✅ **Ingredientes básicos** (ingredientes cadastrados)
- ✅ **Sub-receitas** (outras receitas)
- ✅ **Produtos normais** (produtos do catálogo)
- ✅ **Combos** (combos cadastrados)

### Combos podem conter:
- ✅ **Produtos normais** (produtos do catálogo)
- ✅ **Receitas** (receitas cadastradas)

## Resumo Rápido

### Endpoints de Receitas

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/catalogo/admin/receitas/ingredientes` | Adiciona item (ingrediente/receita/produto/combo) |
| GET | `/api/catalogo/admin/receitas/{receita_id}/ingredientes` | Lista itens de uma receita |
| GET | `/api/catalogo/admin/receitas/com-ingredientes` | Lista receitas com itens detalhados |
| PUT | `/api/catalogo/admin/receitas/ingredientes/{id}` | Atualiza quantidade de um item |
| DELETE | `/api/catalogo/admin/receitas/ingredientes/{id}` | Remove item de uma receita |

### Endpoints de Combos

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/catalogo/admin/combos` | Cria combo com itens (produtos/receitas) |
| PUT | `/api/catalogo/admin/combos/{id}` | Atualiza combo e seus itens |
| GET | `/api/catalogo/admin/combos/{id}` | Busca combo com itens |

## Autenticação

Todos os endpoints requerem autenticação de administrador. Inclua o token no header:

```
Authorization: Bearer <seu_token>
```

---

## 1. Receitas - Adicionar Item

**POST** `/api/catalogo/admin/receitas/ingredientes`

Adiciona um item (ingrediente, receita, produto ou combo) a uma receita.

### Request Body

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

**Opção 3: Produto Normal**
```json
{
  "receita_id": 1,
  "produto_cod_barras": "PROD001",
  "quantidade": 3.0
}
```

**Opção 4: Combo**
```json
{
  "receita_id": 1,
  "combo_id": 2,
  "quantidade": 1.0
}
```

### Campos

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|------------|-----------|
| `receita_id` | integer | Sim | ID da receita que receberá o item |
| `ingrediente_id` | integer | Condicional* | ID do ingrediente básico |
| `receita_ingrediente_id` | integer | Condicional* | ID da receita usada como ingrediente |
| `produto_cod_barras` | string | Condicional* | Código de barras do produto |
| `combo_id` | integer | Condicional* | ID do combo |
| `quantidade` | float | Não | Quantidade do item |

\* **Importante**: Você deve fornecer exatamente um dos campos (`ingrediente_id`, `receita_ingrediente_id`, `produto_cod_barras` ou `combo_id`), nunca múltiplos e nunca nenhum.

### Resposta de Sucesso (201)

```json
{
  "id": 10,
  "receita_id": 1,
  "ingrediente_id": 5,
  "receita_ingrediente_id": null,
  "produto_cod_barras": null,
  "combo_id": null,
  "quantidade": 2.0
}
```

### Erros Possíveis

- **400 Bad Request**: 
  - "Deve fornecer ingrediente_id, receita_ingrediente_id, produto_cod_barras ou combo_id"
  - "Deve fornecer apenas um dos campos..."
  - "Ingrediente já cadastrado nesta receita"
  - "Sub-receita já cadastrada nesta receita"
  - "Produto já cadastrado nesta receita"
  - "Combo já cadastrado nesta receita"
  - "Uma receita não pode ser ingrediente de si mesma"

- **404 Not Found**:
  - "Receita não encontrada"
  - "Ingrediente não encontrado"
  - "Receita ingrediente não encontrada"
  - "Produto não encontrado"
  - "Combo não encontrado"

---

## 2. Receitas - Listar Itens

**GET** `/api/catalogo/admin/receitas/{receita_id}/ingredientes`

Retorna todos os itens (ingredientes, receitas, produtos e combos) de uma receita, opcionalmente filtrados por tipo.

### Query Parameters

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `tipo` | string | Não | Filtrar por tipo de item. Valores válidos: `ingrediente`, `sub-receita`, `produto`, `combo` |

### Exemplos de Uso

**Listar todos os itens:**
```
GET /api/catalogo/admin/receitas/1/ingredientes
```

**Listar apenas ingredientes básicos:**
```
GET /api/catalogo/admin/receitas/1/ingredientes?tipo=ingrediente
```

**Listar apenas sub-receitas:**
```
GET /api/catalogo/admin/receitas/1/ingredientes?tipo=sub-receita
```

**Listar apenas produtos:**
```
GET /api/catalogo/admin/receitas/1/ingredientes?tipo=produto
```

**Listar apenas combos:**
```
GET /api/catalogo/admin/receitas/1/ingredientes?tipo=combo
```

### Resposta de Sucesso (200)

```json
[
  {
    "id": 10,
    "receita_id": 1,
    "ingrediente_id": 5,
    "receita_ingrediente_id": null,
    "produto_cod_barras": null,
    "combo_id": null,
    "quantidade": 2.0
  },
  {
    "id": 11,
    "receita_id": 1,
    "ingrediente_id": null,
    "receita_ingrediente_id": 3,
    "produto_cod_barras": null,
    "combo_id": null,
    "quantidade": 1.5
  },
  {
    "id": 12,
    "receita_id": 1,
    "ingrediente_id": null,
    "receita_ingrediente_id": null,
    "produto_cod_barras": "PROD001",
    "combo_id": null,
    "quantidade": 3.0
  },
  {
    "id": 13,
    "receita_id": 1,
    "ingrediente_id": null,
    "receita_ingrediente_id": null,
    "produto_cod_barras": null,
    "combo_id": 2,
    "quantidade": 1.0
  }
]
```

---

## 3. Receitas - Listar com Itens Detalhados

**GET** `/api/catalogo/admin/receitas/com-ingredientes`

Retorna receitas com seus itens incluídos, com informações detalhadas.

### Query Parameters

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `empresa_id` | integer | Não | Filtrar por empresa |
| `ativo` | boolean | Não | Filtrar apenas receitas ativas |
| `search` | string | Não | Busca textual por nome/descrição |

### Resposta de Sucesso (200)

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
        "produto_cod_barras": null,
        "combo_id": null,
        "quantidade": 2.0,
        "ingrediente_nome": "Farinha",
        "ingrediente_descricao": "Farinha de trigo",
        "ingrediente_unidade_medida": "KG",
        "ingrediente_custo": 5.50,
        "receita_ingrediente_nome": null,
        "receita_ingrediente_descricao": null,
        "receita_ingrediente_preco_venda": null,
        "produto_descricao": null,
        "produto_imagem": null,
        "combo_titulo": null,
        "combo_descricao": null,
        "combo_preco_total": null
      },
      {
        "id": 12,
        "receita_id": 1,
        "ingrediente_id": null,
        "receita_ingrediente_id": null,
        "produto_cod_barras": "PROD001",
        "combo_id": null,
        "quantidade": 3.0,
        "ingrediente_nome": null,
        "ingrediente_descricao": null,
        "ingrediente_unidade_medida": null,
        "ingrediente_custo": null,
        "receita_ingrediente_nome": null,
        "receita_ingrediente_descricao": null,
        "receita_ingrediente_preco_venda": null,
        "produto_descricao": "Queijo Mussarela",
        "produto_imagem": "https://example.com/queijo.jpg",
        "combo_titulo": null,
        "combo_descricao": null,
        "combo_preco_total": null
      },
      {
        "id": 13,
        "receita_id": 1,
        "ingrediente_id": null,
        "receita_ingrediente_id": null,
        "produto_cod_barras": null,
        "combo_id": 2,
        "quantidade": 1.0,
        "ingrediente_nome": null,
        "ingrediente_descricao": null,
        "ingrediente_unidade_medida": null,
        "ingrediente_custo": null,
        "receita_ingrediente_nome": null,
        "receita_ingrediente_descricao": null,
        "receita_ingrediente_preco_venda": null,
        "produto_descricao": null,
        "produto_imagem": null,
        "combo_titulo": "Combo Pizza + Bebida",
        "combo_descricao": "Pizza média com refrigerante",
        "combo_preco_total": 35.00
      }
    ]
  }
]
```

### Como Identificar o Tipo de Item

Para identificar o tipo de item, verifique qual campo não é `null`:

- **Ingrediente Básico**: `ingrediente_id` não é `null`
- **Sub-receita**: `receita_ingrediente_id` não é `null`
- **Produto Normal**: `produto_cod_barras` não é `null`
- **Combo**: `combo_id` não é `null`

---

## 4. Combos - Criar com Itens

**POST** `/api/catalogo/admin/combos`

Cria um novo combo com itens (produtos ou receitas).

### Request Body

```json
{
  "empresa_id": 1,
  "titulo": "Combo Pizza Completo",
  "descricao": "Pizza média com bebida e sobremesa",
  "preco_total": 45.00,
  "custo_total": 15.00,
  "ativo": true,
  "itens": [
    {
      "produto_cod_barras": "PROD001",
      "quantidade": 1
    },
    {
      "receita_id": 3,
      "quantidade": 1
    }
  ]
}
```

### Campos do Item

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|------------|-----------|
| `produto_cod_barras` | string | Condicional* | Código de barras do produto |
| `receita_id` | integer | Condicional* | ID da receita |
| `quantidade` | integer | Sim | Quantidade do item (mínimo 1) |

\* **Importante**: Você deve fornecer exatamente um dos campos (`produto_cod_barras` OU `receita_id`), nunca ambos e nunca nenhum.

### Resposta de Sucesso (201)

```json
{
  "id": 5,
  "empresa_id": 1,
  "titulo": "Combo Pizza Completo",
  "descricao": "Pizza média com bebida e sobremesa",
  "preco_total": 45.00,
  "custo_total": 15.00,
  "ativo": true,
  "imagem": "https://example.com/combo.jpg",
  "itens": [
    {
      "produto_cod_barras": "PROD001",
      "receita_id": null,
      "quantidade": 1
    },
    {
      "produto_cod_barras": null,
      "receita_id": 3,
      "quantidade": 1
    }
  ],
  "created_at": "2026-01-11T10:00:00Z",
  "updated_at": "2026-01-11T10:00:00Z"
}
```

---

## 5. Combos - Atualizar com Itens

**PUT** `/api/catalogo/admin/combos/{id}`

Atualiza um combo e seus itens. Se `itens` for fornecido, substitui todos os itens existentes.

### Request Body

```json
{
  "titulo": "Combo Pizza Completo Atualizado",
  "preco_total": 50.00,
  "itens": [
    {
      "produto_cod_barras": "PROD002",
      "quantidade": 2
    },
    {
      "receita_id": 4,
      "quantidade": 1
    }
  ]
}
```

---

## Exemplos de Uso no Frontend

### Exemplo 1: Adicionar Produto a uma Receita

```typescript
async function adicionarProdutoReceita(receitaId: number, produtoCodBarras: string, quantidade: number) {
  const token = localStorage.getItem('auth_token');
  
  const response = await fetch(`/api/catalogo/admin/receitas/ingredientes`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      receita_id: receitaId,
      produto_cod_barras: produtoCodBarras,
      quantidade: quantidade
    })
  });
  
  if (!response.ok) {
    throw new Error('Erro ao adicionar produto à receita');
  }
  
  return await response.json();
}
```

### Exemplo 2: Adicionar Combo a uma Receita

```typescript
async function adicionarComboReceita(receitaId: number, comboId: number, quantidade: number) {
  const token = localStorage.getItem('auth_token');
  
  const response = await fetch(`/api/catalogo/admin/receitas/ingredientes`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      receita_id: receitaId,
      combo_id: comboId,
      quantidade: quantidade
    })
  });
  
  if (!response.ok) {
    throw new Error('Erro ao adicionar combo à receita');
  }
  
  return await response.json();
}
```

### Exemplo 3: Criar Combo com Receita

```typescript
async function criarComboComReceita(empresaId: number, receitaId: number) {
  const token = localStorage.getItem('auth_token');
  
  const response = await fetch(`/api/catalogo/admin/combos`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      empresa_id: empresaId,
      titulo: "Combo com Receita",
      descricao: "Combo que inclui uma receita",
      preco_total: 30.00,
      ativo: true,
      itens: [
        {
          receita_id: receitaId,
          quantidade: 1
        }
      ]
    })
  });
  
  if (!response.ok) {
    throw new Error('Erro ao criar combo');
  }
  
  return await response.json();
}
```

### Exemplo 4: Renderizar Itens de Receita

```typescript
interface ItemDetalhado {
  id: number;
  receita_id: number;
  ingrediente_id: number | null;
  receita_ingrediente_id: number | null;
  produto_cod_barras: string | null;
  combo_id: number | null;
  quantidade: number | null;
  // Campos detalhados...
}

function renderizarItem(item: ItemDetalhado) {
  if (item.ingrediente_id !== null) {
    // Ingrediente básico
    return (
      <div>
        <h4>🧂 {item.ingrediente_nome}</h4>
        <p>{item.ingrediente_descricao}</p>
        <p>Quantidade: {item.quantidade} {item.ingrediente_unidade_medida}</p>
        <p>Custo: R$ {item.ingrediente_custo}</p>
      </div>
    );
  } else if (item.receita_ingrediente_id !== null) {
    // Sub-receita
    return (
      <div>
        <h4>📋 {item.receita_ingrediente_nome}</h4>
        <p>{item.receita_ingrediente_descricao}</p>
        <p>Quantidade: {item.quantidade} unidade(s)</p>
        <p>Preço: R$ {item.receita_ingrediente_preco_venda}</p>
        <small>Sub-receita</small>
      </div>
    );
  } else if (item.produto_cod_barras !== null) {
    // Produto normal
    return (
      <div>
        <h4>📦 {item.produto_descricao}</h4>
        <img src={item.produto_imagem} alt={item.produto_descricao} />
        <p>Quantidade: {item.quantidade}</p>
        <small>Produto</small>
      </div>
    );
  } else if (item.combo_id !== null) {
    // Combo
    return (
      <div>
        <h4>🎁 {item.combo_titulo}</h4>
        <p>{item.combo_descricao}</p>
        <p>Quantidade: {item.quantidade} unidade(s)</p>
        <p>Preço: R$ {item.combo_preco_total}</p>
        <small>Combo</small>
      </div>
    );
  }
}
```

### Exemplo 5: Formulário para Adicionar Item a Receita

```typescript
function FormularioAdicionarItemReceita({ receitaId }: { receitaId: number }) {
  const [tipo, setTipo] = useState<'ingrediente' | 'receita' | 'produto' | 'combo'>('ingrediente');
  const [ingredienteId, setIngredienteId] = useState<number | null>(null);
  const [receitaIdItem, setReceitaIdItem] = useState<number | null>(null);
  const [produtoCodBarras, setProdutoCodBarras] = useState<string | null>(null);
  const [comboId, setComboId] = useState<number | null>(null);
  const [quantidade, setQuantidade] = useState<number>(1);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const body: any = {
      receita_id: receitaId,
      quantidade: quantidade
    };
    
    if (tipo === 'ingrediente') {
      if (!ingredienteId) {
        alert('Selecione um ingrediente');
        return;
      }
      body.ingrediente_id = ingredienteId;
    } else if (tipo === 'receita') {
      if (!receitaIdItem) {
        alert('Selecione uma receita');
        return;
      }
      body.receita_ingrediente_id = receitaIdItem;
    } else if (tipo === 'produto') {
      if (!produtoCodBarras) {
        alert('Selecione um produto');
        return;
      }
      body.produto_cod_barras = produtoCodBarras;
    } else if (tipo === 'combo') {
      if (!comboId) {
        alert('Selecione um combo');
        return;
      }
      body.combo_id = comboId;
    }
    
    try {
      await adicionarItemReceita(body);
      alert('Item adicionado com sucesso!');
    } catch (error) {
      alert('Erro ao adicionar item');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>
          Tipo de Item:
          <select value={tipo} onChange={(e) => setTipo(e.target.value as any)}>
            <option value="ingrediente">Ingrediente Básico</option>
            <option value="receita">Sub-receita</option>
            <option value="produto">Produto Normal</option>
            <option value="combo">Combo</option>
          </select>
        </label>
      </div>
      
      {tipo === 'ingrediente' && (
        <div>
          <label>
            Ingrediente:
            <select value={ingredienteId || ''} onChange={(e) => setIngredienteId(Number(e.target.value))}>
              <option value="">Selecione um ingrediente</option>
              {/* Lista de ingredientes */}
            </select>
          </label>
        </div>
      )}
      
      {tipo === 'receita' && (
        <div>
          <label>
            Receita:
            <select value={receitaIdItem || ''} onChange={(e) => setReceitaIdItem(Number(e.target.value))}>
              <option value="">Selecione uma receita</option>
              {/* Lista de receitas disponíveis */}
            </select>
          </label>
        </div>
      )}
      
      {tipo === 'produto' && (
        <div>
          <label>
            Produto:
            <select value={produtoCodBarras || ''} onChange={(e) => setProdutoCodBarras(e.target.value)}>
              <option value="">Selecione um produto</option>
              {/* Lista de produtos */}
            </select>
          </label>
        </div>
      )}
      
      {tipo === 'combo' && (
        <div>
          <label>
            Combo:
            <select value={comboId || ''} onChange={(e) => setComboId(Number(e.target.value))}>
              <option value="">Selecione um combo</option>
              {/* Lista de combos */}
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
            min="0.01"
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

### 1. Campos Mutuamente Exclusivos

**Receitas:**
- Forneça exatamente um: `ingrediente_id`, `receita_ingrediente_id`, `produto_cod_barras` ou `combo_id`

**Combos:**
- Forneça exatamente um: `produto_cod_barras` ou `receita_id`

### 2. Referências Circulares

O backend valida que uma receita não pode ser ingrediente de si mesma. O frontend pode prevenir isso mostrando um aviso.

### 3. Duplicatas

O backend retorna erro 400 se tentar adicionar o mesmo item duas vezes. O frontend pode verificar isso antes de enviar.

## Cálculo de Custo

O campo `custo_total` é calculado automaticamente considerando:
- **Ingredientes básicos**: `quantidade × custo_ingrediente`
- **Sub-receitas**: `quantidade × custo_total_da_sub_receita` (recursivo)
- **Produtos**: O custo é calculado baseado no `ProdutoEmpModel` da empresa
- **Combos**: `quantidade × custo_total_do_combo`

O cálculo é feito automaticamente pelo backend.

## Notas Técnicas

1. **Proteção contra Loops**: O sistema previne referências circulares. Se detectar um loop, retorna custo 0 para evitar cálculo infinito.

2. **Performance**: O cálculo de custo de receitas com muitas sub-receitas aninhadas pode ser mais lento. Considere cachear os resultados no frontend.

3. **Cascata de Exclusão**: 
   - Se uma receita for deletada, todos os seus itens são removidos automaticamente
   - Se um item (produto/receita/combo) for deletado, ele é removido de todas as receitas/combos que o utilizam

## Migrações SQL

Execute as seguintes migrações no banco de dados:

1. `2026-01-11_receitas_suportar_produtos_e_combos.sql` - Adiciona suporte a produtos e combos em receitas
2. `2026-01-11_combos_suportar_receitas.sql` - Adiciona suporte a receitas em combos

## Suporte

Para dúvidas ou problemas, consulte a documentação da API ou entre em contato com a equipe de backend.
