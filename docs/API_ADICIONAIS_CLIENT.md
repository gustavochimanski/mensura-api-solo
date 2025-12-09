# 📚 Documentação Client - API de Complementos

## 🎯 Visão Geral

Esta documentação descreve os endpoints **client** para consultar complementos e seus adicionais.

**Autenticação**: Requer token de cliente via header `X-Super-Token`

**Acesso**: Apenas leitura (GET) - não há endpoints de criação/edição para clientes

---

## 🔧 Endpoints Disponíveis

**Base URL**: `/api/catalogo/client/complementos`

### 1. Listar Complementos de um Produto

```http
GET /api/catalogo/client/complementos/produto/{cod_barras}?apenas_ativos=true
X-Super-Token: {token}
```

**Path Parameters:**
- `cod_barras` (required): Código de barras do produto

**Query Parameters:**
- `apenas_ativos` (optional): `true` ou `false` (default: `true`)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "empresa_id": 1,
    "nome": "Molhos",
    "descricao": "Escolha seus molhos",
    "obrigatorio": false,
    "quantitativo": false,
    "permite_multipla_escolha": true,
    "ordem": 0,
    "ativo": true,
    "adicionais": [
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
      },
      {
        "id": 2,
        "nome": "Maionese",
        "descricao": null,
        "preco": 0.0,
        "custo": 0.0,
        "ativo": true,
        "ordem": 1,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    ],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

**Descrição**: Retorna todos os complementos vinculados a um produto específico, incluindo seus adicionais ordenados.

---

### 2. Listar Complementos de um Combo

```http
GET /api/catalogo/client/complementos/combo/{combo_id}?apenas_ativos=true
X-Super-Token: {token}
```

**Path Parameters:**
- `combo_id` (required): ID do combo

**Query Parameters:**
- `apenas_ativos` (optional): `true` ou `false` (default: `true`)

**Response:** `200 OK` (List[ComplementoResponse])

**Descrição**: 
- Retorna todos os complementos disponíveis para um combo
- A lista é construída a partir dos produtos que compõem o combo
- Agrega os complementos vinculados a cada produto do combo
- Remove duplicatas (mesmo complemento aparece apenas uma vez)

**Exemplo de Uso:**
```typescript
const complementos = await fetch(
  '/api/catalogo/client/complementos/combo/1?apenas_ativos=true',
  {
    headers: {
      'X-Super-Token': token
    }
  }
);

const complementosData = await complementos.json();
// Retorna lista de complementos únicos dos produtos do combo
```

---

### 3. Listar Complementos de uma Receita

```http
GET /api/catalogo/client/complementos/receita/{receita_id}?apenas_ativos=true
X-Super-Token: {token}
```

**Path Parameters:**
- `receita_id` (required): ID da receita

**Query Parameters:**
- `apenas_ativos` (optional): `true` ou `false` (default: `true`)

**Response:** `200 OK` (List[ComplementoResponse])

**Descrição**: 
- Atualmente retorna lista vazia `[]`
- Receitas não têm produtos diretamente vinculados
- Pode ser expandido no futuro se houver necessidade de vincular complementos diretamente a receitas

---

## 📊 Schemas

### ComplementoResponse
```typescript
interface ComplementoResponse {
  id: number;
  empresa_id: number;
  nome: string;
  descricao?: string;
  obrigatorio: boolean;
  quantitativo: boolean;
  permite_multipla_escolha: boolean;
  ordem: number;
  ativo: boolean;
  adicionais: AdicionalResponse[];  // Lista de adicionais vinculados (ordenados)
  created_at: string;               // ISO 8601
  updated_at: string;                // ISO 8601
}
```

### AdicionalResponse
```typescript
interface AdicionalResponse {
  id: number;                      // ID do adicional (usado como adicional_id nos pedidos)
  nome: string;
  descricao?: string;
  preco: number;
  custo: number;
  ativo: boolean;
  ordem: number;                   // Ordem dentro do complemento
  created_at: string;              // ISO 8601
  updated_at: string;               // ISO 8601
}
```

---

## 💡 Exemplos de Uso

### Exemplo 1: Buscar Complementos de um Produto

```typescript
async function buscarComplementosProduto(codBarras: string, token: string) {
  const response = await fetch(
    `/api/catalogo/client/complementos/produto/${codBarras}?apenas_ativos=true`,
    {
      headers: {
        'X-Super-Token': token
      }
    }
  );

  if (!response.ok) {
    throw new Error('Erro ao buscar complementos');
  }

  const complementos = await response.json();
  
  // Processar complementos
  complementos.forEach(complemento => {
    console.log(`Complemento: ${complemento.nome}`);
    console.log(`Obrigatório: ${complemento.obrigatorio}`);
    console.log(`Permite múltipla escolha: ${complemento.permite_multipla_escolha}`);
    
    // Processar adicionais
    complemento.adicionais.forEach(adicional => {
      console.log(`  - ${adicional.nome}: R$ ${adicional.preco}`);
    });
  });

  return complementos;
}

// Uso
const complementos = await buscarComplementosProduto('7891234567890', clienteToken);
```

### Exemplo 2: Buscar Complementos de um Combo

```typescript
async function buscarComplementosCombo(comboId: number, token: string) {
  const response = await fetch(
    `/api/catalogo/client/complementos/combo/${comboId}?apenas_ativos=true`,
    {
      headers: {
        'X-Super-Token': token
      }
    }
  );

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Combo não encontrado ou inativo');
    }
    throw new Error('Erro ao buscar complementos');
  }

  const complementos = await response.json();
  return complementos;
}

// Uso
const complementos = await buscarComplementosCombo(1, clienteToken);
```

### Exemplo 3: Renderizar Complementos no Frontend

```typescript
// React/TypeScript exemplo
function ComplementosProduto({ codBarras }: { codBarras: string }) {
  const [complementos, setComplementos] = useState<ComplementoResponse[]>([]);
  const token = useClienteToken();

  useEffect(() => {
    buscarComplementosProduto(codBarras, token)
      .then(setComplementos)
      .catch(console.error);
  }, [codBarras, token]);

  return (
    <div>
      {complementos.map(complemento => (
        <div key={complemento.id}>
          <h3>{complemento.nome}</h3>
          {complemento.obrigatorio && <span>Obrigatório</span>}
          
          {complemento.permite_multipla_escolha ? (
            // Checkboxes para múltipla escolha
            complemento.adicionais.map(adicional => (
              <label key={adicional.id}>
                <input type="checkbox" value={adicional.id} />
                {adicional.nome} - R$ {adicional.preco.toFixed(2)}
              </label>
            ))
          ) : (
            // Radio buttons para escolha única
            complemento.adicionais.map(adicional => (
              <label key={adicional.id}>
                <input type="radio" name={`complemento-${complemento.id}`} value={adicional.id} />
                {adicional.nome} - R$ {adicional.preco.toFixed(2)}
              </label>
            ))
          )}
        </div>
      ))}
    </div>
  );
}
```

---

## 📝 Tabela de Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/catalogo/client/complementos/produto/{cod_barras}` | Listar complementos de um produto |
| GET | `/api/catalogo/client/complementos/combo/{combo_id}` | Listar complementos de um combo |
| GET | `/api/catalogo/client/complementos/receita/{receita_id}` | Listar complementos de uma receita |

---

## 🔍 Códigos de Status HTTP

- `200 OK`: Sucesso
- `400 Bad Request`: Dados inválidos
- `401 Unauthorized`: Token inválido ou ausente
- `404 Not Found`: Recurso não encontrado (produto/combo/receita)
- `422 Unprocessable Entity`: Erro de validação

---

## ⚠️ Observações Importantes

1. **Autenticação**: Todos os endpoints requerem header `X-Super-Token` válido
2. **Apenas Leitura**: Clientes não podem criar, editar ou deletar complementos/adicionais
3. **Filtro de Ativos**: Por padrão, apenas complementos e adicionais ativos são retornados
4. **Ordem**: Os adicionais são retornados ordenados pela coluna `ordem` do vínculo
5. **Combo**: Retorna complementos únicos (sem duplicatas) dos produtos do combo
6. **Receita**: Atualmente retorna lista vazia (funcionalidade futura)

---

## 🔐 Autenticação

### Header Obrigatório

```http
X-Super-Token: {token_do_cliente}
```

O token é obtido através do processo de autenticação do cliente (fora do escopo desta documentação).

### Exemplo de Requisição Completa

```typescript
const response = await fetch(
  '/api/catalogo/client/complementos/produto/7891234567890?apenas_ativos=true',
  {
    method: 'GET',
    headers: {
      'X-Super-Token': 'seu-token-aqui',
      'Content-Type': 'application/json'
    }
  }
);
```

---

**Documentação Admin**: `docs/API_ADICIONAIS_ADMIN.md`

