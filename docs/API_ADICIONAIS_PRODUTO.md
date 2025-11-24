# API - Listar Adicionais de um Produto

## Endpoint

**GET** `/api/catalogo/admin/adicionais/produto/{cod_barras}`

**Tag:** `Admin - Catalogo - Adicionais`

**Autenticação:** Requerida (Admin)

---

## Descrição

Lista todos os adicionais vinculados a um produto específico, identificado pelo código de barras.

---

## Parâmetros

### Path Parameters

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `cod_barras` | `string` | Sim | Código de barras do produto |

### Query Parameters

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `apenas_ativos` | `boolean` | Não | `true` | Se `true`, retorna apenas adicionais ativos. Se `false`, retorna todos os adicionais (ativos e inativos) |

---

## Resposta

### Status Code: `200 OK`

### Schema de Resposta

**Tipo:** `List[AdicionalResponse]`

```json
[
  {
    "id": 1,
    "empresa_id": 1,
    "nome": "Queijo Extra",
    "descricao": "Adicione queijo extra ao produto",
    "preco": 3.50,
    "custo": 1.00,
    "ativo": true,
    "obrigatorio": false,
    "permite_multipla_escolha": true,
    "ordem": 1,
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  },
  {
    "id": 2,
    "empresa_id": 1,
    "nome": "Bacon",
    "descricao": "Adicione bacon ao produto",
    "preco": 4.00,
    "custo": 1.50,
    "ativo": true,
    "obrigatorio": false,
    "permite_multipla_escolha": true,
    "ordem": 2,
    "created_at": "2024-01-15T10:35:00",
    "updated_at": "2024-01-15T10:35:00"
  }
]
```

### Campos do AdicionalResponse

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | `integer` | ID único do adicional |
| `empresa_id` | `integer` | ID da empresa dona do adicional |
| `nome` | `string` | Nome do adicional |
| `descricao` | `string` \| `null` | Descrição do adicional (opcional) |
| `preco` | `float` | Preço do adicional |
| `custo` | `float` | Custo do adicional |
| `ativo` | `boolean` | Indica se o adicional está ativo |
| `obrigatorio` | `boolean` | Indica se o adicional é obrigatório para o produto |
| `permite_multipla_escolha` | `boolean` | Indica se permite selecionar múltiplas quantidades do mesmo adicional |
| `ordem` | `integer` | Ordem de exibição do adicional |
| `created_at` | `datetime` | Data e hora de criação |
| `updated_at` | `datetime` | Data e hora da última atualização |

---

## Exemplos de Requisição

### Exemplo 1: Listar apenas adicionais ativos (padrão)

```http
GET /api/catalogo/admin/adicionais/produto/7891234567890?apenas_ativos=true
Authorization: Bearer {token}
```

**Resposta:**
```json
[
  {
    "id": 1,
    "empresa_id": 1,
    "nome": "Queijo Extra",
    "descricao": "Adicione queijo extra ao produto",
    "preco": 3.50,
    "custo": 1.00,
    "ativo": true,
    "obrigatorio": false,
    "permite_multipla_escolha": true,
    "ordem": 1,
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  }
]
```

### Exemplo 2: Listar todos os adicionais (ativos e inativos)

```http
GET /api/catalogo/admin/adicionais/produto/7891234567890?apenas_ativos=false
Authorization: Bearer {token}
```

**Resposta:**
```json
[
  {
    "id": 1,
    "empresa_id": 1,
    "nome": "Queijo Extra",
    "descricao": "Adicione queijo extra ao produto",
    "preco": 3.50,
    "custo": 1.00,
    "ativo": true,
    "obrigatorio": false,
    "permite_multipla_escolha": true,
    "ordem": 1,
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  },
  {
    "id": 3,
    "empresa_id": 1,
    "nome": "Cebola (Desativado)",
    "descricao": null,
    "preco": 2.00,
    "custo": 0.50,
    "ativo": false,
    "obrigatorio": false,
    "permite_multipla_escolha": true,
    "ordem": 3,
    "created_at": "2024-01-10T08:00:00",
    "updated_at": "2024-01-20T14:00:00"
  }
]
```

### Exemplo 3: Produto sem adicionais

```http
GET /api/catalogo/admin/adicionais/produto/7891234567891?apenas_ativos=true
Authorization: Bearer {token}
```

**Resposta:**
```json
[]
```

---

## Códigos de Erro

### 404 Not Found

**Quando:** Produto não encontrado

**Resposta:**
```json
{
  "detail": "Produto não encontrado."
}
```

### 401 Unauthorized

**Quando:** Token de autenticação inválido ou ausente

**Resposta:**
```json
{
  "detail": "Não autenticado"
}
```

### 403 Forbidden

**Quando:** Usuário não tem permissão de admin

**Resposta:**
```json
{
  "detail": "Acesso negado"
}
```

---

## Observações

1. **Código de Barras:** O endpoint utiliza o código de barras do produto, não o ID. Se você tiver apenas o ID do produto, será necessário buscar o produto primeiro para obter o código de barras.

2. **Filtro de Ativos:** Por padrão, apenas adicionais ativos são retornados. Para incluir adicionais inativos, defina `apenas_ativos=false`.

3. **Lista Vazia:** Se o produto não tiver adicionais vinculados, a API retorna uma lista vazia `[]` com status `200 OK`.

4. **Ordem:** Os adicionais são retornados ordenados pelo campo `ordem` (menor para maior).

5. **Vínculo:** Os adicionais retornados são apenas aqueles que foram explicitamente vinculados ao produto através do endpoint de vinculação.

---

## Endpoints Relacionados

- **Vincular Adicionais a Produto:** `POST /api/catalogo/admin/adicionais/produto/{cod_barras}/vincular`
- **Listar Todos os Adicionais:** `GET /api/catalogo/admin/adicionais?empresa_id={id}`
- **Buscar Adicional por ID:** `GET /api/catalogo/admin/adicionais/{adicional_id}`
- **Criar Adicional:** `POST /api/catalogo/admin/adicionais`
- **Atualizar Adicional:** `PUT /api/catalogo/admin/adicionais/{adicional_id}`
- **Deletar Adicional:** `DELETE /api/catalogo/admin/adicionais/{adicional_id}`

---

## Exemplo de Uso com cURL

```bash
curl -X GET \
  "https://api.exemplo.com/api/catalogo/admin/adicionais/produto/7891234567890?apenas_ativos=true" \
  -H "Authorization: Bearer seu_token_aqui" \
  -H "Content-Type: application/json"
```

---

## Exemplo de Uso com JavaScript (Fetch)

```javascript
const codBarras = '7891234567890';
const apenasAtivos = true;

fetch(`/api/catalogo/admin/adicionais/produto/${codBarras}?apenas_ativos=${apenasAtivos}`, {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
  .then(response => response.json())
  .then(data => {
    console.log('Adicionais do produto:', data);
  })
  .catch(error => {
    console.error('Erro ao buscar adicionais:', error);
  });
```

---

## Exemplo de Uso com Python (Requests)

```python
import requests

cod_barras = '7891234567890'
apenas_ativos = True
token = 'seu_token_aqui'

url = f'https://api.exemplo.com/api/catalogo/admin/adicionais/produto/{cod_barras}'
params = {'apenas_ativos': apenas_ativos}
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

response = requests.get(url, params=params, headers=headers)
adicionais = response.json()

print('Adicionais do produto:', adicionais)
```

