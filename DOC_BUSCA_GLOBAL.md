# Documentação: Busca Global de Produtos, Receitas e Combos

## Visão Geral

O endpoint de busca global permite pesquisar produtos, receitas e combos em um único endpoint, retornando resultados unificados e organizados por tipo.

## Endpoints

### Admin

**Endpoint:** `GET /api/catalogo/admin/busca/global`

**Autenticação:** Requer autenticação de admin

### Cliente

**Endpoint:** `GET /api/catalogo/client/busca/global`

**Autenticação:** Requer header `X-Super-Token` com o token do cliente

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `empresa_id` | int | Sim | - | ID da empresa |
| `termo` | string | Sim | - | Termo de busca (mínimo 1 caractere) |
| `apenas_disponiveis` | boolean | Não | `true` | Filtrar apenas itens disponíveis (produtos/receitas) |
| `apenas_ativos` | boolean | Não | `true` | Filtrar apenas itens ativos |
| `limit` | int | Não | `50` | Limite de resultados por tipo (máximo: 200) |

## O que é buscado

### Produtos
- **Campos buscados:** Descrição e código de barras
- **Filtros aplicados:** Ativo, disponível (se `apenas_disponiveis=true`)

### Receitas
- **Campos buscados:** Nome e descrição
- **Filtros aplicados:** Ativo, disponível (se `apenas_disponiveis=true`)

### Combos
- **Campos buscados:** Título e descrição
- **Filtros aplicados:** Apenas ativo (combos não têm campo disponível)

## Resposta

```typescript
{
  produtos: Array<{
    tipo: "produto";
    id: string;              // código de barras
    cod_barras: string;
    nome: string;            // descrição do produto
    descricao: string;
    imagem: string | null;
    preco: number;           // preco_venda
    preco_venda: number;
    disponivel: boolean;
    ativo: boolean;
    empresa_id: number;
  }>;
  receitas: Array<{
    tipo: "receita";
    id: number;              // receita_id
    receita_id: number;
    nome: string;
    descricao: string | null;
    imagem: string | null;
    preco: number;           // preco_venda
    preco_venda: number;
    disponivel: boolean;
    ativo: boolean;
    empresa_id: number;
  }>;
  combos: Array<{
    tipo: "combo";
    id: number;              // combo_id
    combo_id: number;
    nome: string;            // título do combo
    titulo: string;
    descricao: string;
    imagem: string | null;
    preco: number;           // preco_total
    preco_total: number;
    disponivel: null;        // combos não têm campo disponível
    ativo: boolean;
    empresa_id: number;
  }>;
  total: number;             // Total de resultados encontrados
}
```

## Exemplos de Uso

### Exemplo 1: Busca simples

```bash
GET /api/catalogo/admin/busca/global?empresa_id=1&termo=pizza
```

**Resposta:**
```json
{
  "produtos": [
    {
      "tipo": "produto",
      "id": "7891234567890",
      "cod_barras": "7891234567890",
      "nome": "Pizza Margherita",
      "descricao": "Pizza Margherita",
      "imagem": "https://...",
      "preco": 25.90,
      "preco_venda": 25.90,
      "disponivel": true,
      "ativo": true,
      "empresa_id": 1
    }
  ],
  "receitas": [
    {
      "tipo": "receita",
      "id": 5,
      "receita_id": 5,
      "nome": "Pizza Artesanal",
      "descricao": "Receita especial de pizza",
      "imagem": null,
      "preco": 30.00,
      "preco_venda": 30.00,
      "disponivel": true,
      "ativo": true,
      "empresa_id": 1
    }
  ],
  "combos": [
    {
      "tipo": "combo",
      "id": 3,
      "combo_id": 3,
      "nome": "Combo Pizza + Bebida",
      "titulo": "Combo Pizza + Bebida",
      "descricao": "Pizza média + refrigerante",
      "imagem": null,
      "preco": 35.90,
      "preco_total": 35.90,
      "disponivel": null,
      "ativo": true,
      "empresa_id": 1
    }
  ],
  "total": 3
}
```

### Exemplo 2: Busca com filtros

```bash
GET /api/catalogo/admin/busca/global?empresa_id=1&termo=refrigerante&apenas_disponiveis=true&apenas_ativos=true&limit=20
```

### Exemplo 3: Busca incluindo inativos

```bash
GET /api/catalogo/admin/busca/global?empresa_id=1&termo=coca&apenas_ativos=false
```

## Integração no Frontend

### Exemplo em TypeScript/JavaScript

```typescript
interface BuscaGlobalItem {
  tipo: "produto" | "receita" | "combo";
  id: string | number;
  nome: string;
  descricao: string | null;
  imagem: string | null;
  preco: number;
  disponivel: boolean | null;
  ativo: boolean;
  empresa_id: number;
  // Campos específicos
  cod_barras?: string;
  receita_id?: number;
  combo_id?: number;
  preco_venda?: number;
  preco_total?: number;
  titulo?: string;
}

interface BuscaGlobalResponse {
  produtos: BuscaGlobalItem[];
  receitas: BuscaGlobalItem[];
  combos: BuscaGlobalItem[];
  total: number;
}

async function buscarGlobal(
  empresaId: number,
  termo: string,
  apenasDisponiveis: boolean = true,
  apenasAtivos: boolean = true,
  limit: number = 50
): Promise<BuscaGlobalResponse> {
  const params = new URLSearchParams({
    empresa_id: empresaId.toString(),
    termo,
    apenas_disponiveis: apenasDisponiveis.toString(),
    apenas_ativos: apenasAtivos.toString(),
    limit: limit.toString(),
  });

  const response = await fetch(
    `/api/catalogo/admin/busca/global?${params}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  return response.json();
}

// Uso
const resultados = await buscarGlobal(1, "pizza");
console.log(`Encontrados ${resultados.total} resultados`);
console.log(`Produtos: ${resultados.produtos.length}`);
console.log(`Receitas: ${resultados.receitas.length}`);
console.log(`Combos: ${resultados.combos.length}`);
```

### Exemplo de renderização unificada

```typescript
function renderizarResultados(resultados: BuscaGlobalResponse) {
  // Combina todos os resultados em uma lista unificada
  const todosItens = [
    ...resultados.produtos,
    ...resultados.receitas,
    ...resultados.combos,
  ];

  return todosItens.map((item) => (
    <div key={`${item.tipo}-${item.id}`}>
      <h3>{item.nome}</h3>
      <p>{item.descricao}</p>
      <span>R$ {item.preco.toFixed(2)}</span>
      {item.tipo === "produto" && <span>Produto</span>}
      {item.tipo === "receita" && <span>Receita</span>}
      {item.tipo === "combo" && <span>Combo</span>}
    </div>
  ));
}
```

## Observações

1. **Busca case-insensitive**: A busca não diferencia maiúsculas e minúsculas
2. **Busca parcial**: A busca usa `LIKE` com `%termo%`, então encontra resultados parciais
3. **Limite por tipo**: O parâmetro `limit` se aplica a cada tipo (produtos, receitas, combos) separadamente
4. **Combos sem disponível**: Combos não possuem campo `disponivel`, então esse campo será `null` para combos
5. **Campos unificados**: Todos os itens têm campos comuns (`tipo`, `id`, `nome`, `preco`, etc.) para facilitar renderização unificada no frontend

## Tratamento de Erros

- **400 Bad Request**: Parâmetros inválidos (empresa_id <= 0, termo vazio, limit fora do range)
- **401 Unauthorized**: Não autenticado (para endpoint de cliente)
- **403 Forbidden**: Sem permissão (para endpoint de admin)

## Performance

- A busca é otimizada com índices nos campos de busca (descrição, nome, título)
- Limite padrão de 50 resultados por tipo para evitar sobrecarga
- Máximo de 200 resultados por tipo

