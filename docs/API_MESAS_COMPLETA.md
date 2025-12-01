# Documentação Completa - API de Mesas

## Base URL

```
${NEXT_PUBLIC_API_URL}/api/mesas/admin/mesas
```

## Autenticação

Todos os endpoints requerem autenticação via Bearer Token no header:

```
Authorization: Bearer {token}
```

O token é obtido do cookie `access_token`.

---

## Schemas de Resposta

### MesaResponse

Schema completo de resposta para uma mesa:

```typescript
{
  id: number                    // ID único da mesa
  codigo: string               // Código da mesa (convertido para string)
  numero: string               // Número da mesa (string)
  descricao: string | null     // Descrição/nome da mesa
  capacidade: number           // Capacidade máxima de pessoas
  status: "D" | "O" | "R"      // Status: D=Disponível, O=Ocupada, R=Reservada
  status_descricao: string     // Descrição do status (ex: "Disponível")
  ativa: "S" | "N"             // "S" ou "N" - se a mesa está ativa
  label: string                // Label para exibição (ex: "Mesa 1")
  num_pessoas_atual?: number | null  // Número atual de pessoas na mesa (opcional)
  empresa_id?: number          // ID da empresa (opcional)
  pedidos_abertos?: Array<{    // Lista de pedidos abertos na mesa (opcional)
    id: number
    numero_pedido: string
    status: string
    num_pessoas?: number | null
    valor_total: number
    cliente_id?: number | null
    cliente_nome?: string | null
  }>
}
```

### PedidoAbertoMesa

Schema para pedido aberto em uma mesa:

```typescript
{
  id: number
  numero_pedido: string
  status: string                // Status do pedido (P, I, R, etc.)
  num_pessoas?: number | null   // Número de pessoas (apenas para pedidos de mesa)
  valor_total: number           // Valor total do pedido
  cliente_id?: number | null    // ID do cliente
  cliente_nome?: string | null  // Nome do cliente
}
```

### MesaStatsResponse

Schema para estatísticas de mesas:

```typescript
{
  total: number        // Total de mesas
  disponiveis: number  // Mesas com status "D"
  ocupadas: number     // Mesas com status "O"
  reservadas: number   // Mesas com status "R"
  inativas: number     // Mesas inativas (ativa = "N")
}
```

---

## Endpoints

### 1. Listar Mesas

**Endpoint:** `GET /api/mesas/admin/mesas`

**Query Parameters:**
- `empresa_id` (obrigatório): ID da empresa

**Resposta de Sucesso (200):**

```json
[
  {
    "id": 1,
    "codigo": "1",
    "numero": "1",
    "descricao": "Mesa 1",
    "capacidade": 4,
    "status": "D",
    "status_descricao": "Disponível",
    "ativa": "S",
    "label": "Mesa 1",
    "num_pessoas_atual": 2,
    "empresa_id": 1,
    "pedidos_abertos": [
      {
        "id": 123,
        "numero_pedido": "PED-001",
        "status": "A",
        "num_pessoas": 2,
        "valor_total": 45.50,
        "cliente_id": 10,
        "cliente_nome": "João Silva"
      }
    ]
  }
]
```

**Resposta de Erro:**

```json
{
  "detail": "Mensagem de erro"
}
```

---

### 2. Buscar Mesas (Search)

**Endpoint:** `GET /api/mesas/admin/mesas/search`

**Query Parameters:**
- `empresa_id` (obrigatório): ID da empresa
- `q` (opcional): Termo de busca (busca por número/descrição)
- `status` (opcional): Filtrar por status ("D", "O" ou "R")
- `ativa` (opcional): Filtrar por status ativo ("S" ou "N")
- `limit` (opcional): Limite de resultados (default: 30, max: 100)
- `offset` (opcional): Offset para paginação (default: 0)

**Exemplo de Requisição:**

```
GET /api/mesas/admin/mesas/search?empresa_id=1&q=mesa&status=D&limit=20
```

**Resposta de Sucesso (200):**

Mesma estrutura do endpoint de listar mesas (array de objetos Mesa).

---

### 3. Buscar Mesa por ID

**Endpoint:** `GET /api/mesas/admin/mesas/{mesaId}`

**Query Parameters:**
- `empresa_id` (obrigatório): ID da empresa

**Path Parameters:**
- `mesaId`: ID da mesa

**Resposta de Sucesso (200):**

```json
{
  "id": 1,
  "codigo": "1",
  "numero": "1",
  "descricao": "Mesa 1",
  "capacidade": 4,
  "status": "D",
  "status_descricao": "Disponível",
  "ativa": "S",
  "label": "Mesa 1",
  "num_pessoas_atual": 2,
  "empresa_id": 1,
  "pedidos_abertos": []
}
```

**Resposta de Erro (404):**

```json
{
  "detail": "Mesa não encontrada"
}
```

---

### 4. Criar Mesa

**Endpoint:** `POST /api/mesas/admin/mesas`

**Query Parameters:**
- `empresa_id` (obrigatório): ID da empresa

**Body (JSON):**

```json
{
  "codigo": 1,
  "descricao": "Mesa 1",
  "capacidade": 4,
  "status": "D",
  "ativa": "S",
  "empresa_id": 1
}
```

**Validações:**

- `codigo`: obrigatório, deve ser > 0
- `descricao`: obrigatório, não pode ser vazio
- `capacidade`: obrigatório, deve ser > 0
- `status`: obrigatório, deve ser "D", "O" ou "R"
- `ativa`: obrigatório, deve ser "S" ou "N"
- `empresa_id`: obrigatório, deve ser > 0 e corresponder ao `empresa_id` da query

**Resposta de Sucesso (201):**

Retorna o objeto Mesa criado (mesma estrutura do GET por ID).

**Resposta de Erro (400):**

```json
{
  "detail": "Já existe uma mesa com código 1 nesta empresa"
}
```

---

### 5. Atualizar Mesa

**Endpoint:** `PUT /api/mesas/admin/mesas/{mesaId}`

**Query Parameters:**
- `empresa_id` (obrigatório): ID da empresa

**Path Parameters:**
- `mesaId`: ID da mesa

**Body (JSON) - Todos os campos são opcionais:**

```json
{
  "descricao": "Mesa 1 - Atualizada",
  "capacidade": 6,
  "status": "O",
  "ativa": "S",
  "empresa_id": 1
}
```

**Validações:**

- `capacidade`: se fornecido, deve ser > 0
- `status`: se fornecido, deve ser "D", "O" ou "R"
- `ativa`: se fornecido, deve ser "S" ou "N"
- `empresa_id`: se fornecido, deve corresponder ao `empresa_id` da query

**Resposta de Sucesso (200):**

Retorna o objeto Mesa atualizado.

**Resposta de Erro (404):**

```json
{
  "detail": "Mesa não encontrada"
}
```

---

### 6. Deletar Mesa

**Endpoint:** `DELETE /api/mesas/admin/mesas/{mesaId}`

**Query Parameters:**
- `empresa_id` (obrigatório): ID da empresa

**Path Parameters:**
- `mesaId`: ID da mesa

**Resposta de Sucesso (200):**

```json
{}
```

**Resposta de Erro (404):**

```json
{
  "detail": "Mesa não encontrada"
}
```

---

### 7. Atualizar Status da Mesa

**Endpoint:** `PATCH /api/mesas/admin/mesas/{mesaId}/status`

**Query Parameters:**
- `empresa_id` (obrigatório): ID da empresa

**Path Parameters:**
- `mesaId`: ID da mesa

**Body (JSON):**

```json
{
  "status": "O"
}
```

**Validações:**

- `status`: obrigatório, deve ser "D", "O" ou "R"

**Resposta de Sucesso (200):**

Retorna o objeto Mesa atualizado.

---

### 8. Ocupar Mesa

**Endpoint:** `POST /api/mesas/admin/mesas/{mesaId}/ocupar`

**Query Parameters:**
- `empresa_id` (obrigatório): ID da empresa

**Path Parameters:**
- `mesaId`: ID da mesa

**Body:** Vazio (sem body)

**Resposta de Sucesso (200):**

Retorna o objeto Mesa com status atualizado para "O" (Ocupada).

**Exemplo de Resposta:**

```json
{
  "id": 1,
  "codigo": "1",
  "numero": "1",
  "descricao": "Mesa 1",
  "capacidade": 4,
  "status": "O",
  "status_descricao": "Ocupada",
  "ativa": "S",
  "label": "Mesa 1",
  "num_pessoas_atual": null,
  "empresa_id": 1,
  "pedidos_abertos": null
}
```

---

### 9. Liberar Mesa

**Endpoint:** `POST /api/mesas/admin/mesas/{mesaId}/liberar`

**Query Parameters:**
- `empresa_id` (obrigatório): ID da empresa

**Path Parameters:**
- `mesaId`: ID da mesa

**Body:** Vazio (sem body)

**Resposta de Sucesso (200):**

Retorna o objeto Mesa com status atualizado para "D" (Disponível) e `cliente_atual_id` limpo.

**Exemplo de Resposta:**

```json
{
  "id": 1,
  "codigo": "1",
  "numero": "1",
  "descricao": "Mesa 1",
  "capacidade": 4,
  "status": "D",
  "status_descricao": "Disponível",
  "ativa": "S",
  "label": "Mesa 1",
  "num_pessoas_atual": null,
  "empresa_id": 1,
  "pedidos_abertos": null
}
```

---

### 10. Reservar Mesa

**Endpoint:** `POST /api/mesas/admin/mesas/{mesaId}/reservar`

**Query Parameters:**
- `empresa_id` (obrigatório): ID da empresa

**Path Parameters:**
- `mesaId`: ID da mesa

**Body:** Vazio (sem body)

**Resposta de Sucesso (200):**

Retorna o objeto Mesa com status atualizado para "R" (Reservada).

**Exemplo de Resposta:**

```json
{
  "id": 1,
  "codigo": "1",
  "numero": "1",
  "descricao": "Mesa 1",
  "capacidade": 4,
  "status": "R",
  "status_descricao": "Reservada",
  "ativa": "S",
  "label": "Mesa 1",
  "num_pessoas_atual": null,
  "empresa_id": 1,
  "pedidos_abertos": null
}
```

---

### 11. Estatísticas das Mesas

**Endpoint:** `GET /api/mesas/admin/mesas/stats`

**Query Parameters:**
- `empresa_id` (obrigatório): ID da empresa

**Resposta de Sucesso (200):**

```json
{
  "total": 20,
  "disponiveis": 12,
  "ocupadas": 5,
  "reservadas": 2,
  "inativas": 1
}
```

**Estrutura do Schema MesaStatsResponse:**

```typescript
{
  total: number        // Total de mesas
  disponiveis: number  // Mesas com status "D"
  ocupadas: number     // Mesas com status "O"
  reservadas: number   // Mesas com status "R"
  inativas: number     // Mesas inativas (ativa = "N")
}
```

---

## Schemas de Request

### MesaCreate

Schema para criar uma mesa:

```typescript
{
  codigo: number      // Código da mesa (deve ser > 0)
  descricao: string   // Descrição da mesa (min_length: 1)
  capacidade: number  // Capacidade máxima (deve ser > 0)
  status: "D" | "O" | "R"  // Status inicial
  ativa: "S" | "N"    // Se a mesa está ativa
  empresa_id: number  // ID da empresa (deve ser > 0)
}
```

**Validações:**
- `codigo`: Deve ser maior que 0
- `descricao`: Não pode ser vazio
- `capacidade`: Deve ser maior que 0
- `status`: Deve ser "D", "O" ou "R"
- `ativa`: Deve ser "S" ou "N"

### MesaUpdate

Schema para atualizar uma mesa (todos os campos são opcionais):

```typescript
{
  descricao?: string   // Descrição da mesa
  capacidade?: number  // Capacidade máxima
  status?: "D" | "O" | "R"  // Status
  ativa?: "S" | "N"    // Se a mesa está ativa
  empresa_id?: number  // ID da empresa
}
```

**Validações:**
- `capacidade`: Se fornecido, deve ser > 0
- `status`: Se fornecido, deve ser "D", "O" ou "R"
- `ativa`: Se fornecido, deve ser "S" ou "N"

### MesaStatusUpdate

Schema para atualizar apenas o status:

```typescript
{
  status: "D" | "O" | "R"  // Novo status
}
```

---

## Resumo dos Status

- **D**: Disponível
- **O**: Ocupada
- **R**: Reservada

## Resumo dos Campos de Ativação

- **S**: Ativa
- **N**: Inativa

---

## Observações Importantes

1. **empresa_id**: Sempre obrigatório como query parameter em todos os endpoints

2. **Autenticação**: Todos os endpoints requerem Bearer Token

3. **Content-Type**: `application/json` para requisições com body

4. **Erros**: Sempre retornam no formato `{ "detail": "mensagem" }`

5. **Pedidos Abertos**: O campo `pedidos_abertos` é opcional e pode não estar presente em todas as respostas. Quando presente, inclui pedidos de mesa (tipo MESA) e pedidos de balcão (tipo BALCAO) que estão associados à mesa e com status aberto.

6. **num_pessoas_atual**: Campo opcional que indica quantas pessoas estão atualmente na mesa, calculado a partir da soma de `num_pessoas` dos pedidos de mesa abertos.

7. **Código vs Número**: O `codigo` é um Decimal no banco de dados, mas é convertido para string na resposta. O `numero` é gerado automaticamente a partir do `codigo` na criação da mesa.

8. **Validações de Unicidade**: 
   - Não é possível criar duas mesas com o mesmo `codigo` na mesma empresa
   - Não é possível criar duas mesas com o mesmo `numero` na mesma empresa

---

## Códigos de Status HTTP

- **200**: Sucesso (GET, PUT, PATCH, DELETE)
- **201**: Criado com sucesso (POST)
- **400**: Erro de validação ou requisição inválida
- **403**: Acesso negado (mesa não pertence à empresa)
- **404**: Recurso não encontrado
- **422**: Erro de validação de dados

---

## Exemplos de Uso

### Listar todas as mesas de uma empresa

```bash
curl -X GET "https://api.example.com/api/mesas/admin/mesas?empresa_id=1" \
  -H "Authorization: Bearer {token}"
```

### Buscar mesas disponíveis

```bash
curl -X GET "https://api.example.com/api/mesas/admin/mesas/search?empresa_id=1&status=D&ativa=S" \
  -H "Authorization: Bearer {token}"
```

### Criar uma nova mesa

```bash
curl -X POST "https://api.example.com/api/mesas/admin/mesas?empresa_id=1" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "codigo": 5,
    "descricao": "Mesa 5",
    "capacidade": 6,
    "status": "D",
    "ativa": "S",
    "empresa_id": 1
  }'
```

### Ocupar uma mesa

```bash
curl -X POST "https://api.example.com/api/mesas/admin/mesas/1/ocupar?empresa_id=1" \
  -H "Authorization: Bearer {token}"
```

### Obter estatísticas

```bash
curl -X GET "https://api.example.com/api/mesas/admin/mesas/stats?empresa_id=1" \
  -H "Authorization: Bearer {token}"
```

---

## Implementação Técnica

### Arquivos Criados

1. **Schemas**: `app/api/cadastros/schemas/schema_mesa.py`
   - `PedidoAbertoMesa`
   - `MesaCreate`
   - `MesaUpdate`
   - `MesaStatusUpdate`
   - `MesaResponse`
   - `MesaStatsResponse`

2. **Service**: `app/api/cadastros/services/service_mesas.py`
   - Lógica de negócio
   - Integração com repositório
   - Integração com pedidos abertos

3. **Repository**: `app/api/cadastros/repositories/repo_mesas.py`
   - Métodos CRUD
   - Operações de status
   - Estatísticas

4. **Router**: `app/api/cadastros/router/admin/router_mesas.py`
   - Todos os 11 endpoints
   - Validações
   - Documentação

### Integração com Pedidos

A API de mesas está integrada com a API de pedidos para:

- Buscar pedidos abertos associados à mesa
- Calcular número atual de pessoas na mesa
- Incluir informações de pedidos nas respostas

Os pedidos abertos incluem:
- Pedidos de mesa (`tipo_entrega = MESA`)
- Pedidos de balcão (`tipo_entrega = BALCAO`)

Ambos são buscados quando estão com status aberto (P, I, R, A, etc.) e associados à mesa pelo campo `mesa_id`.

