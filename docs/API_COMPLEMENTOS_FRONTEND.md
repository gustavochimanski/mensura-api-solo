# 📚 Documentação API de Complementos - Frontend

## 📋 Índice
1. [Visão Geral](#visão-geral)
2. [Estrutura dos Modelos](#estrutura-dos-modelos)
3. [Relacionamentos](#relacionamentos)
4. [Schemas](#schemas)
5. [Endpoints Admin](#endpoints-admin)
6. [Endpoints Client](#endpoints-client)
7. [Uso em Pedidos](#uso-em-pedidos)
8. [Exemplos Práticos](#exemplos-práticos)

---

## 🎯 Visão Geral

O sistema de **Complementos** permite criar grupos de itens (adicionais) que podem ser vinculados a produtos. Cada complemento pode ter múltiplos itens, e cada item tem preço próprio.

### Conceitos Principais

- **Complemento**: Grupo de itens com configurações (ex: "Molhos", "Tamanhos", "Extras")
- **Item de Complemento** (Adicional): Item individual dentro de um complemento (ex: "Ketchup", "Maionese", "Pequeno", "Grande")

### Estrutura Hierárquica

```
Empresa
  └── Complemento (grupo)
       ├── Item 1 (adicional)
       ├── Item 2 (adicional)
       └── Item 3 (adicional)
```

---

## 🗄️ Estrutura dos Modelos

### 1. ComplementoModel (Tabela: `complemento_produto`)

Representa um **grupo de itens** com configurações.

```typescript
interface Complemento {
  id: number;
  empresa_id: number;
  nome: string;                    // Ex: "Molhos", "Tamanhos", "Extras"
  descricao?: string;
  
  // Configurações
  obrigatorio: boolean;             // Se o complemento é obrigatório
  quantitativo: boolean;            // Se permite quantidade (ex: 2x bacon)
  permite_multipla_escolha: boolean; // Se pode escolher múltiplos itens
  ativo: boolean;
  ordem: number;                    // Ordem de exibição
  
  // Timestamps
  created_at: string;
  updated_at: string;
  
  // Relacionamentos
  adicionais: Adicional[];          // Lista de itens do complemento
}
```

### 2. AdicionalModel (Tabela: `complemento_itens`)

Representa um **item individual** dentro de um complemento.

```typescript
interface Adicional {
  id: number;                      // ID do item (adicional_id nos pedidos)
  empresa_id: number;
  complemento_id: number;          // FK para o complemento
  
  nome: string;                    // Ex: "Ketchup", "Maionese", "Pequeno"
  descricao?: string;
  preco: number;                   // Preço do item
  custo: number;                   // Custo interno
  ativo: boolean;
  ordem: number;                   // Ordem dentro do complemento
  
  // Timestamps
  created_at: string;
  updated_at: string;
}
```

---

## 🔗 Relacionamentos

### Diagrama de Relacionamentos

```
Empresa (1) ──< (N) Complemento (1) ──< (N) Adicional (Item)
                │
                │ (N:N via produto_complemento_link)
                │
                └──> (N) Produto
```

### Relacionamentos Detalhados

1. **Empresa → Complemento**: 1:N
   - Uma empresa pode ter vários complementos
   - Cada complemento pertence a uma empresa

2. **Complemento → Adicional (Item)**: 1:N
   - Um complemento pode ter vários itens
   - Cada item pertence a um complemento
   - **CASCADE DELETE**: Se deletar o complemento, deleta os itens

3. **Produto → Complemento**: N:N
   - Um produto pode ter vários complementos
   - Um complemento pode estar em vários produtos
   - Relacionamento via tabela `produto_complemento_link`

---

## 📦 Schemas

### Requests (Admin)

#### CriarComplementoRequest
```typescript
interface CriarComplementoRequest {
  empresa_id: number;
  nome: string;                    // 1-100 caracteres
  descricao?: string;              // Máx 255 caracteres
  obrigatorio?: boolean;           // Default: false
  quantitativo?: boolean;         // Default: false
  permite_multipla_escolha?: boolean; // Default: true
  ordem?: number;                  // Default: 0
}
```

#### AtualizarComplementoRequest
```typescript
interface AtualizarComplementoRequest {
  nome?: string;
  descricao?: string;
  obrigatorio?: boolean;
  quantitativo?: boolean;
  permite_multipla_escolha?: boolean;
  ativo?: boolean;
  ordem?: number;
}
```

#### CriarAdicionalRequest
```typescript
interface CriarAdicionalRequest {
  nome: string;                    // 1-100 caracteres
  descricao?: string;             // Máx 255 caracteres
  preco: number;                   // Decimal (18,2) - Default: 0
  custo: number;                   // Decimal (18,2) - Default: 0
  ativo?: boolean;                // Default: true
  ordem?: number;                 // Default: 0
}
```

#### AtualizarAdicionalRequest
```typescript
interface AtualizarAdicionalRequest {
  nome?: string;
  descricao?: string;
  preco?: number;
  custo?: number;
  ativo?: boolean;
  ordem?: number;
}
```

#### VincularComplementosProdutoRequest
```typescript
interface VincularComplementosProdutoRequest {
  complemento_ids: number[];       // Array de IDs dos complementos
}
```

### Responses

#### ComplementoResponse
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
  adicionais: AdicionalResponse[]; // Lista de itens
  created_at: string;              // ISO 8601
  updated_at: string;              // ISO 8601
}
```

#### AdicionalResponse
```typescript
interface AdicionalResponse {
  id: number;                      // Este é o adicional_id usado nos pedidos
  nome: string;
  descricao?: string;
  preco: number;
  custo: number;
  ativo: boolean;
  ordem: number;
  created_at: string;              // ISO 8601
  updated_at: string;              // ISO 8601
}
```

#### ComplementoResumidoResponse
```typescript
interface ComplementoResumidoResponse {
  id: number;
  nome: string;
  obrigatorio: boolean;
  quantitativo: boolean;
  permite_multipla_escolha: boolean;
  ordem: number;
}
```

#### VincularComplementosProdutoResponse
```typescript
interface VincularComplementosProdutoResponse {
  produto_cod_barras: string;
  complementos_vinculados: ComplementoResumidoResponse[];
  message: string;                 // "Complementos vinculados com sucesso"
}
```

---

## 🔧 Endpoints Admin

**Base URL**: `/api/catalogo/admin/complementos`

**Autenticação**: Requer token de admin (via `get_current_user`)

### 1. Listar Complementos

```http
GET /api/catalogo/admin/complementos/?empresa_id={id}&apenas_ativos=true
```

**Query Parameters:**
- `empresa_id` (required): ID da empresa
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
        "descricao": null,
        "preco": 0.0,
        "custo": 0.0,
        "ativo": true,
        "ordem": 0,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    ],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### 2. Criar Complemento

```http
POST /api/catalogo/admin/complementos/
```

**Request Body:**
```json
{
  "empresa_id": 1,
  "nome": "Tamanhos",
  "descricao": "Escolha o tamanho",
  "obrigatorio": true,
  "quantitativo": false,
  "permite_multipla_escolha": false,
  "ordem": 1
}
```

**Response:** `201 Created` (ComplementoResponse)

### 3. Buscar Complemento por ID

```http
GET /api/catalogo/admin/complementos/{complemento_id}
```

**Response:** `200 OK` (ComplementoResponse)

### 4. Atualizar Complemento

```http
PUT /api/catalogo/admin/complementos/{complemento_id}
```

**Request Body:**
```json
{
  "nome": "Tamanhos Atualizado",
  "ativo": false
}
```

**Response:** `200 OK` (ComplementoResponse)

### 5. Deletar Complemento

```http
DELETE /api/catalogo/admin/complementos/{complemento_id}
```

**Response:** `200 OK`
```json
{
  "message": "Complemento deletado com sucesso"
}
```

⚠️ **Atenção**: Deletar um complemento também deleta todos os seus itens (CASCADE).

### 6. Vincular Complementos a Produto

```http
POST /api/catalogo/admin/complementos/produto/{cod_barras}/vincular
```

**Request Body:**
```json
{
  "complemento_ids": [1, 2, 3]
}
```

**Response:** `200 OK` (VincularComplementosProdutoResponse)

### 7. Listar Complementos de um Produto

```http
GET /api/catalogo/admin/complementos/produto/{cod_barras}?apenas_ativos=true
```

**Response:** `200 OK` (List[ComplementoResponse])

---

### 8. Criar Item (Adicional) em Complemento

```http
POST /api/catalogo/admin/complementos/{complemento_id}/adicionais
```

**Request Body:**
```json
{
  "nome": "Ketchup",
  "descricao": "Molho de tomate",
  "preco": 2.50,
  "custo": 1.00,
  "ativo": true,
  "ordem": 0
}
```

**Response:** `201 Created` (AdicionalResponse)

### 9. Listar Itens de um Complemento

```http
GET /api/catalogo/admin/complementos/{complemento_id}/adicionais?apenas_ativos=true
```

**Response:** `200 OK` (List[AdicionalResponse])

### 10. Atualizar Item (Adicional)

```http
PUT /api/catalogo/admin/complementos/{complemento_id}/adicionais/{adicional_id}
```

**Request Body:**
```json
{
  "preco": 3.00,
  "ativo": false
}
```

**Response:** `200 OK` (AdicionalResponse)

### 11. Deletar Item (Adicional)

```http
DELETE /api/catalogo/admin/complementos/{complemento_id}/adicionais/{adicional_id}
```

**Response:** `200 OK`
```json
{
  "message": "Adicional deletado com sucesso"
}
```

---

## 👤 Endpoints Client

**Base URL**: `/api/catalogo/client/complementos`

**Autenticação**: Requer header `X-Super-Token` do cliente

### 1. Listar Complementos de um Produto

```http
GET /api/catalogo/client/complementos/produto/{cod_barras}?apenas_ativos=true
```

**Headers:**
```
X-Super-Token: {token_do_cliente}
```

**Response:** `200 OK` (List[ComplementoResponse])

**Exemplo de Uso:**
```typescript
// Buscar complementos disponíveis para um produto
const complementos = await fetch(
  `/api/catalogo/client/complementos/produto/7891234567890?apenas_ativos=true`,
  {
    headers: {
      'X-Super-Token': clienteToken
    }
  }
);
```

### 2. Listar Complementos de um Combo

```http
GET /api/catalogo/client/complementos/combo/{combo_id}?apenas_ativos=true
```

**Response:** `200 OK` (List[ComplementoResponse])

**Nota**: Retorna os complementos agregados de todos os produtos do combo.

### 3. Listar Complementos de uma Receita

```http
GET /api/catalogo/client/complementos/receita/{receita_id}?apenas_ativos=true
```

**Response:** `200 OK` (List[ComplementoResponse])

**Nota**: Atualmente retorna lista vazia (funcionalidade futura).

---

## 🛒 Uso em Pedidos

### Schema de Request para Pedidos

#### ItemComplementoRequest
```typescript
interface ItemComplementoRequest {
  complemento_id: number;
  adicionais: ItemAdicionalComplementoRequest[];
}

interface ItemAdicionalComplementoRequest {
  adicional_id: number;            // ID do item (AdicionalResponse.id)
  quantidade: number;              // Quantidade (usado se complemento.quantitativo = true)
}
```

#### ItemPedidoRequest (com complementos)
```typescript
interface ItemPedidoRequest {
  produto_cod_barras: string;
  quantidade: number;
  observacao?: string;
  complementos?: ItemComplementoRequest[];
}
```

### Exemplo de Pedido com Complementos

```json
{
  "empresa_id": 1,
  "endereco_id": 123,
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "7891234567890",
        "quantidade": 2,
        "observacao": "Sem cebola",
        "complementos": [
          {
            "complemento_id": 1,    // ID do complemento "Molhos"
            "adicionais": [
              {
                "adicional_id": 1,  // ID do item "Ketchup"
                "quantidade": 1
              },
              {
                "adicional_id": 2,  // ID do item "Maionese"
                "quantidade": 1
              }
            ]
          },
          {
            "complemento_id": 2,    // ID do complemento "Tamanhos"
            "adicionais": [
              {
                "adicional_id": 5,  // ID do item "Grande"
                "quantidade": 1
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### Regras de Validação

1. **Complemento Obrigatório**: Se `complemento.obrigatorio = true`, deve selecionar pelo menos 1 item
2. **Quantitativo**: Se `complemento.quantitativo = true`, pode escolher quantidade > 1 do mesmo item
3. **Múltipla Escolha**: Se `complemento.permite_multipla_escolha = true`, pode selecionar vários itens diferentes
4. **Única Escolha**: Se `complemento.permite_multipla_escolha = false`, deve selecionar apenas 1 item

### Response de Pedido (Snapshot)

O pedido retorna um snapshot dos complementos selecionados:

```typescript
interface ProdutoPedidoAdicionalOut {
  adicional_id?: number;
  nome?: string;
  quantidade: number;
  preco_unitario: number;
  total: number;
}

interface ProdutoPedidoItemOut {
  item_id?: number;
  produto_cod_barras?: string;
  descricao?: string;
  imagem?: string;
  quantidade: number;
  preco_unitario: number;
  observacao?: string;
  adicionais: ProdutoPedidoAdicionalOut[];
}
```

---

## 💡 Exemplos Práticos

### Exemplo 1: Criar um Complemento "Tamanhos" com Itens

```typescript
// 1. Criar o complemento
const complemento = await fetch('/api/catalogo/admin/complementos/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${adminToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    empresa_id: 1,
    nome: "Tamanhos",
    descricao: "Escolha o tamanho",
    obrigatorio: true,
    quantitativo: false,
    permite_multipla_escolha: false,
    ordem: 1
  })
});

const complementoData = await complemento.json();
const complementoId = complementoData.id;

// 2. Criar os itens
const itens = [
  { nome: "Pequeno", preco: 0, ordem: 0 },
  { nome: "Médio", preco: 2.00, ordem: 1 },
  { nome: "Grande", preco: 4.00, ordem: 2 }
];

for (const item of itens) {
  await fetch(`/api/catalogo/admin/complementos/${complementoId}/adicionais`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${adminToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(item)
  });
}
```

### Exemplo 2: Vincular Complemento a um Produto

```typescript
await fetch(`/api/catalogo/admin/complementos/produto/7891234567890/vincular`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${adminToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    complemento_ids: [1, 2]  // IDs dos complementos
  })
});
```

### Exemplo 3: Frontend - Exibir Complementos no Cardápio

```typescript
// 1. Buscar complementos do produto
const complementos = await fetch(
  `/api/catalogo/client/complementos/produto/${produto.cod_barras}`,
  {
    headers: {
      'X-Super-Token': clienteToken
    }
  }
).then(r => r.json());

// 2. Renderizar na UI
complementos.forEach(complemento => {
  // Se obrigatório, mostrar aviso
  if (complemento.obrigatorio) {
    console.log(`⚠️ ${complemento.nome} é obrigatório`);
  }
  
  // Renderizar itens
  complemento.adicionais.forEach(item => {
    console.log(`- ${item.nome} - R$ ${item.preco.toFixed(2)}`);
  });
});
```

### Exemplo 4: Frontend - Adicionar Item ao Carrinho com Complementos

```typescript
const adicionarAoCarrinho = (produto, complementosSelecionados) => {
  const item = {
    produto_cod_barras: produto.cod_barras,
    quantidade: 1,
    complementos: complementosSelecionados.map(comp => ({
      complemento_id: comp.id,
      adicionais: comp.itensSelecionados.map(item => ({
        adicional_id: item.id,
        quantidade: item.quantidade || 1
      }))
    }))
  };
  
  // Validar antes de enviar
  complementosSelecionados.forEach(comp => {
    if (comp.obrigatorio && comp.itensSelecionados.length === 0) {
      throw new Error(`${comp.nome} é obrigatório`);
    }
    
    if (!comp.permite_multipla_escolha && comp.itensSelecionados.length > 1) {
      throw new Error(`${comp.nome} permite apenas uma escolha`);
    }
  });
  
  return item;
};
```

### Exemplo 5: Calcular Total com Complementos

```typescript
const calcularTotalItem = (produto, quantidade, complementosSelecionados) => {
  let total = produto.preco * quantidade;
  
  complementosSelecionados.forEach(comp => {
    comp.itensSelecionados.forEach(item => {
      const qtd = comp.quantitativo ? item.quantidade : 1;
      total += item.preco * qtd * quantidade;
    });
  });
  
  return total;
};
```

---

## ⚠️ Observações Importantes

1. **IDs nos Pedidos**: Use `adicional_id` (que é o `id` do `AdicionalResponse`) nos pedidos
2. **Tabela no Banco**: A tabela é `complemento_itens`, mas o modelo Python ainda se chama `AdicionalModel`
3. **CASCADE DELETE**: Deletar um complemento deleta todos os seus itens automaticamente
4. **Validação Frontend**: Sempre valide no frontend antes de enviar:
   - Complementos obrigatórios
   - Múltipla escolha vs escolha única
   - Quantidades (se quantitativo)
5. **Ordem**: Use o campo `ordem` para controlar a exibição na UI
6. **Ativo**: Sempre filtre por `ativo = true` na listagem para clientes

---

## 🔍 Códigos de Status HTTP

- `200 OK`: Sucesso
- `201 Created`: Criado com sucesso
- `400 Bad Request`: Dados inválidos
- `401 Unauthorized`: Não autenticado
- `403 Forbidden`: Sem permissão
- `404 Not Found`: Recurso não encontrado
- `422 Unprocessable Entity`: Erro de validação

---

## 📞 Suporte

Para dúvidas ou problemas, consulte a documentação da API ou entre em contato com a equipe de desenvolvimento.

