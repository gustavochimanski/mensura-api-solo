# Documentação - Acerto de Entregadores (Frontend)

## 📋 Visão Geral

O sistema de **Acerto de Entregadores** permite gerenciar o fechamento financeiro de pedidos entregues por entregadores. O sistema calcula automaticamente os valores devidos aos entregadores considerando:
- Valor total dos pedidos entregues
- Valor da diária do entregador (quando configurado)
- Valor líquido (soma dos pedidos + diária)

## 🔐 Autenticação

Todos os endpoints requerem autenticação de usuário admin. O token deve ser enviado no header:
```
Authorization: Bearer <token>
```

## 📍 Base URL

```
/api/financeiro/admin/acertos-entregadores
```

---

## 🛠️ Endpoints

### 1. Listar Pedidos Pendentes de Acerto

Lista todos os pedidos entregues que ainda não foram acertados no período especificado.

**Endpoint:** `GET /pendentes`

**Query Parameters:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `empresa_id` | `integer` | ✅ Sim | ID da empresa |
| `inicio` | `string` | ✅ Sim | Data/hora inicial (formato: `YYYY-MM-DD` ou ISO datetime `YYYY-MM-DDTHH:mm:ss`) |
| `fim` | `string` | ✅ Sim | Data/hora final (formato: `YYYY-MM-DD` ou ISO datetime `YYYY-MM-DDTHH:mm:ss`) |
| `entregador_id` | `integer` | ❌ Opcional | ID do entregador (filtra por entregador específico) |

**Exemplo de Requisição:**
```http
GET /api/financeiro/admin/acertos-entregadores/pendentes?empresa_id=1&inicio=2024-01-01&fim=2024-01-31&entregador_id=5
```

**Resposta (200 OK):**
```json
[
  {
    "id": 123,
    "entregador_id": 5,
    "valor_total": 45.50,
    "data_criacao": "2024-01-15T14:30:00",
    "cliente_id": 10,
    "status": "E"
  },
  {
    "id": 124,
    "entregador_id": 5,
    "valor_total": 32.00,
    "data_criacao": "2024-01-15T18:45:00",
    "cliente_id": 11,
    "status": "E"
  }
]
```

**Regras de Negócio:**
- Retorna apenas pedidos com:
  - `tipo_entrega = DELIVERY`
  - `status = "E"` (Entregue)
  - `acertado_entregador = false`
  - `entregador_id` não nulo
  - Criados no período especificado
- Ordenados por data de criação (mais antigos primeiro)

---

### 2. Preview do Acerto

Retorna um resumo detalhado dos valores que serão acertados, agrupados por entregador e por dia. **Não realiza o acerto**, apenas mostra o que será acertado.

**Endpoint:** `GET /preview`

**Query Parameters:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `empresa_id` | `integer` | ✅ Sim | ID da empresa |
| `inicio` | `string` | ✅ Sim | Data/hora inicial (formato: `YYYY-MM-DD` ou ISO datetime) |
| `fim` | `string` | ✅ Sim | Data/hora final (formato: `YYYY-MM-DD` ou ISO datetime) |
| `entregador_id` | `integer` | ❌ Opcional | ID do entregador (filtra por entregador específico) |

**Exemplo de Requisição:**
```http
GET /api/financeiro/admin/acertos-entregadores/preview?empresa_id=1&inicio=2024-01-01&fim=2024-01-31
```

**Resposta (200 OK):**
```json
{
  "empresa_id": 1,
  "inicio": "2024-01-01T00:00:00",
  "fim": "2024-01-31T23:59:59",
  "entregador_id": null,
  "resumos": [
    {
      "data": "2024-01-15",
      "entregador_id": 5,
      "entregador_nome": "João Silva",
      "valor_diaria": 50.00,
      "qtd_pedidos": 3,
      "valor_pedidos": 120.50,
      "valor_liquido": 170.50
    },
    {
      "data": "2024-01-16",
      "entregador_id": 5,
      "entregador_nome": "João Silva",
      "valor_diaria": 50.00,
      "qtd_pedidos": 2,
      "valor_pedidos": 85.00,
      "valor_liquido": 135.00
    },
    {
      "data": "2024-01-15",
      "entregador_id": 7,
      "entregador_nome": "Maria Santos",
      "valor_diaria": 60.00,
      "qtd_pedidos": 4,
      "valor_pedidos": 200.00,
      "valor_liquido": 260.00
    }
  ],
  "total_pedidos": 9,
  "total_bruto": 405.50,
  "total_diarias": 160.00,
  "total_liquido": 565.50
}
```

**Campos da Resposta:**
- `resumos`: Array de resumos agrupados por (entregador, dia)
  - `data`: Data do pedido (formato: `YYYY-MM-DD`)
  - `entregador_id`: ID do entregador
  - `entregador_nome`: Nome do entregador
  - `valor_diaria`: Valor da diária configurada para o entregador (pode ser `null` ou `0`)
  - `qtd_pedidos`: Quantidade de pedidos naquele dia
  - `valor_pedidos`: Soma do valor total dos pedidos
  - `valor_liquido`: `valor_pedidos + valor_diaria`
- `total_pedidos`: Total de pedidos no período
- `total_bruto`: Soma de todos os valores dos pedidos
- `total_diarias`: Soma de todas as diárias (considerando entregadores distintos)
- `total_liquido`: `total_bruto + total_diarias`

**Regras de Negócio:**
- Agrupa por entregador e por dia (data de criação do pedido)
- Considera apenas pedidos pendentes de acerto
- Se `entregador_id` for fornecido, retorna apenas resumos daquele entregador
- A diária é contabilizada uma vez por dia por entregador (mesmo que o entregador tenha múltiplos pedidos no mesmo dia)

---

### 3. Fechar Pedidos (Realizar Acerto)

Marca os pedidos como acertados e calcula os valores totais. **Esta operação é irreversível** - os pedidos ficam marcados como acertados permanentemente.

**Endpoint:** `POST /fechar`

**Body (JSON):**
```json
{
  "empresa_id": 1,
  "inicio": "2024-01-01T00:00:00",
  "fim": "2024-01-31T23:59:59",
  "entregador_id": 5,
  "fechado_por": "Nome do Usuário"
}
```

**Campos do Request:**
| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `empresa_id` | `integer` | ✅ Sim | ID da empresa (deve ser > 0) |
| `inicio` | `datetime` | ✅ Sim | Data/hora inicial do período |
| `fim` | `datetime` | ✅ Sim | Data/hora final do período |
| `entregador_id` | `integer` | ❌ Opcional | ID do entregador (se fornecido, acerta apenas pedidos deste entregador) |
| `fechado_por` | `string` | ❌ Opcional | Nome de quem está realizando o fechamento (aparece na mensagem de resposta) |

**Exemplo de Requisição:**
```http
POST /api/financeiro/admin/acertos-entregadores/fechar
Content-Type: application/json

{
  "empresa_id": 1,
  "inicio": "2024-01-01T00:00:00",
  "fim": "2024-01-31T23:59:59",
  "entregador_id": 5,
  "fechado_por": "Admin Sistema"
}
```

**Resposta (200 OK):**
```json
{
  "pedidos_fechados": 5,
  "pedido_ids": [123, 124, 125, 126, 127],
  "valor_total": 405.50,
  "valor_diaria_total": 50.00,
  "valor_liquido": 455.50,
  "inicio": "2024-01-01T00:00:00",
  "fim": "2024-01-31T23:59:59",
  "mensagem": "Pedidos marcados como acertados por Admin Sistema"
}
```

**Campos da Resposta:**
- `pedidos_fechados`: Quantidade de pedidos marcados como acertados
- `pedido_ids`: Array com os IDs dos pedidos acertados
- `valor_total`: Soma do valor total de todos os pedidos acertados
- `valor_diaria_total`: Soma das diárias dos entregadores envolvidos
  - Se `entregador_id` foi fornecido: usa a diária daquele entregador
  - Se não foi fornecido: soma as diárias de todos os entregadores distintos que tiveram pedidos acertados
- `valor_liquido`: `valor_total + valor_diaria_total`
- `inicio` / `fim`: Período utilizado
- `mensagem`: Mensagem informativa (inclui `fechado_por` se fornecido)

**Resposta quando não há pedidos:**
```json
{
  "pedidos_fechados": 0,
  "pedido_ids": [],
  "valor_total": 0,
  "valor_diaria_total": 0,
  "valor_liquido": 0,
  "inicio": "2024-01-01T00:00:00",
  "fim": "2024-01-31T23:59:59",
  "mensagem": "Nenhum pedido encontrado para o período."
}
```

**Regras de Negócio:**
- Marca os pedidos com:
  - `acertado_entregador = true`
  - `acertado_entregador_em = timestamp atual`
  - `data_atualizacao = timestamp atual`
- A operação é atômica (todos os pedidos são marcados ou nenhum)
- Se não houver pedidos no período, retorna resposta com valores zerados

---

### 4. Consultar Acertos Passados

Retorna um resumo dos pedidos que já foram acertados no período especificado. Útil para consultar histórico de acertos.

**Endpoint:** `GET /passados`

**Query Parameters:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `empresa_id` | `integer` | ✅ Sim | ID da empresa |
| `inicio` | `string` | ✅ Sim | Data/hora inicial (formato: `YYYY-MM-DD` ou ISO datetime) |
| `fim` | `string` | ✅ Sim | Data/hora final (formato: `YYYY-MM-DD` ou ISO datetime) |
| `entregador_id` | `integer` | ❌ Opcional | ID do entregador (filtra por entregador específico) |

**Exemplo de Requisição:**
```http
GET /api/financeiro/admin/acertos-entregadores/passados?empresa_id=1&inicio=2024-01-01&fim=2024-01-31
```

**Resposta (200 OK):**
```json
{
  "empresa_id": 1,
  "inicio": "2024-01-01T00:00:00",
  "fim": "2024-01-31T23:59:59",
  "entregador_id": null,
  "resumos": [
    {
      "data": "2024-01-10",
      "entregador_id": 5,
      "entregador_nome": "João Silva",
      "valor_diaria": 50.00,
      "qtd_pedidos": 2,
      "valor_pedidos": 90.00,
      "valor_liquido": 140.00
    }
  ],
  "total_pedidos": 2,
  "total_bruto": 90.00,
  "total_diarias": 50.00,
  "total_liquido": 140.00
}
```

**Regras de Negócio:**
- Retorna apenas pedidos com `acertado_entregador = true`
- Filtra por `acertado_entregador_em` (data em que foi acertado), não pela data de criação do pedido
- Estrutura de resposta idêntica ao endpoint `/preview`
- Agrupa por entregador e por dia (data de criação do pedido)

---

## 📅 Formato de Datas

O sistema aceita dois formatos de data/hora:

1. **Data simples** (sem horário): `YYYY-MM-DD`
   - Exemplo: `2024-01-15`
   - Para `inicio`: considera `00:00:00`
   - Para `fim`: considera `23:59:59` e adiciona 1 dia (limite exclusivo)

2. **ISO DateTime**: `YYYY-MM-DDTHH:mm:ss` ou `YYYY-MM-DDTHH:mm:ss.ssssss`
   - Exemplo: `2024-01-15T14:30:00`
   - Exemplo: `2024-01-15T14:30:00.123456`

**Importante:** O sistema usa limite superior **exclusivo** para evitar problemas com microsegundos. Se você passar uma data sem horário como `fim`, o sistema automaticamente considera até o final do dia seguinte.

---

## 💡 Fluxo Recomendado de Uso

### 1. Visualizar Pedidos Pendentes
```http
GET /pendentes?empresa_id=1&inicio=2024-01-01&fim=2024-01-31
```
- Use para listar todos os pedidos que precisam ser acertados
- Permite verificar detalhes individuais de cada pedido

### 2. Visualizar Preview do Acerto
```http
GET /preview?empresa_id=1&inicio=2024-01-01&fim=2024-01-31
```
- Use para ver um resumo consolidado antes de fechar
- Mostra valores agrupados por entregador e dia
- Permite validar os cálculos antes de confirmar

### 3. Realizar o Fechamento
```http
POST /fechar
{
  "empresa_id": 1,
  "inicio": "2024-01-01T00:00:00",
  "fim": "2024-01-31T23:59:59",
  "fechado_por": "Nome do Usuário"
}
```
- Confirma e marca os pedidos como acertados
- **Operação irreversível**

### 4. Consultar Histórico (Opcional)
```http
GET /passados?empresa_id=1&inicio=2024-01-01&fim=2024-01-31
```
- Use para consultar acertos já realizados
- Útil para relatórios e auditoria

---

## ⚠️ Regras de Negócio Importantes

### Filtros Aplicados
Todos os endpoints consideram apenas:
- Pedidos do tipo `DELIVERY`
- Pedidos com `entregador_id` não nulo
- Para pendentes/preview: `status = "E"` (Entregue) e `acertado_entregador = false`
- Para passados: `acertado_entregador = true`

### Cálculo de Diária
- A diária é obtida do campo `valor_diaria` do entregador
- Se o entregador não tiver diária configurada, o valor será `0` ou `null`
- No cálculo de `valor_liquido`, a diária é somada ao valor dos pedidos
- Quando múltiplos entregadores são acertados, cada um tem sua diária contabilizada

### Agrupamento
- O preview e acertos passados agrupam por (entregador, dia)
- O dia é baseado na data de **criação do pedido** (`created_at`)
- Cada combinação (entregador, dia) gera um resumo separado

### Valores Monetários
- Todos os valores são retornados como `float` com 2 casas decimais
- O sistema usa `Decimal` internamente para evitar problemas de precisão
- Valores `null` são convertidos para `0.0`

---

## 🔍 Exemplos de Uso no Frontend

### Exemplo 1: Listar Pendentes e Fechar
```javascript
// 1. Listar pedidos pendentes
const pendentes = await fetch(
  `/api/financeiro/admin/acertos-entregadores/pendentes?empresa_id=1&inicio=2024-01-01&fim=2024-01-31`,
  { headers: { Authorization: `Bearer ${token}` } }
).then(r => r.json());

// 2. Ver preview
const preview = await fetch(
  `/api/financeiro/admin/acertos-entregadores/preview?empresa_id=1&inicio=2024-01-01&fim=2024-01-31`,
  { headers: { Authorization: `Bearer ${token}` } }
).then(r => r.json());

// 3. Fechar pedidos
const resultado = await fetch(
  `/api/financeiro/admin/acertos-entregadores/fechar`,
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({
      empresa_id: 1,
      inicio: '2024-01-01T00:00:00',
      fim: '2024-01-31T23:59:59',
      fechado_por: 'Usuário Logado'
    })
  }
).then(r => r.json());
```

### Exemplo 2: Filtrar por Entregador
```javascript
// Preview apenas para um entregador específico
const preview = await fetch(
  `/api/financeiro/admin/acertos-entregadores/preview?empresa_id=1&inicio=2024-01-01&fim=2024-01-31&entregador_id=5`,
  { headers: { Authorization: `Bearer ${token}` } }
).then(r => r.json());
```

### Exemplo 3: Consultar Histórico
```javascript
// Ver acertos já realizados no mês
const historico = await fetch(
  `/api/financeiro/admin/acertos-entregadores/passados?empresa_id=1&inicio=2024-01-01&fim=2024-01-31`,
  { headers: { Authorization: `Bearer ${token}` } }
).then(r => r.json());

console.log(`Total acertado: R$ ${historico.total_liquido.toFixed(2)}`);
```

---

## 🎨 Sugestões de Interface

### Tela de Acerto de Entregadores

1. **Filtros no topo:**
   - Seleção de empresa (obrigatório)
   - Data inicial e final
   - Filtro opcional por entregador (dropdown)

2. **Aba "Pendentes":**
   - Tabela com lista de pedidos pendentes (endpoint `/pendentes`)
   - Colunas: ID, Entregador, Valor, Data, Cliente
   - Botão "Ver Preview" que chama `/preview`

3. **Aba "Preview":**
   - Tabela agrupada por entregador e dia (endpoint `/preview`)
   - Mostrar: Data, Entregador, Qtd Pedidos, Valor Pedidos, Diária, Valor Líquido
   - Totais no rodapé: Total Pedidos, Total Bruto, Total Diárias, Total Líquido
   - Botão "Confirmar Acerto" que chama `/fechar` com confirmação

4. **Aba "Histórico":**
   - Tabela similar ao preview (endpoint `/passados`)
   - Mostrar acertos já realizados
   - Filtros de período

5. **Modal de Confirmação:**
   - Ao clicar em "Confirmar Acerto", mostrar modal com:
     - Resumo dos valores
     - Quantidade de pedidos
     - Campo opcional "Fechado por"
   - Botões: "Cancelar" e "Confirmar"

---

## ❌ Tratamento de Erros

### Erro 401 - Não Autenticado
```json
{
  "detail": "Not authenticated"
}
```
**Solução:** Verificar se o token de autenticação está sendo enviado corretamente.

### Erro 422 - Validação
```json
{
  "detail": [
    {
      "loc": ["query", "empresa_id"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt"
    }
  ]
}
```
**Solução:** Verificar se os parâmetros obrigatórios estão corretos e dentro dos limites esperados.

### Erro 500 - Erro Interno
```json
{
  "detail": "Internal server error"
}
```
**Solução:** Verificar logs do servidor. Pode ser problema de conexão com banco de dados ou erro inesperado.

---

## 📝 Notas Finais

- Todos os endpoints são **idempotentes** (exceto `/fechar` que altera estado)
- O endpoint `/fechar` pode ser chamado múltiplas vezes, mas apenas pedidos ainda não acertados serão processados
- Recomenda-se sempre chamar `/preview` antes de `/fechar` para validar os valores
- O sistema não cria registros de "acerto" separados - apenas marca os pedidos como acertados
- A diária é configurada no cadastro do entregador e pode ser `null` ou `0`

---

## 🔗 Endpoints Resumidos

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/pendentes` | Lista pedidos pendentes de acerto |
| `GET` | `/preview` | Preview do acerto (não realiza) |
| `POST` | `/fechar` | Realiza o acerto (marca pedidos) |
| `GET` | `/passados` | Consulta acertos já realizados |

---

**Última atualização:** Janeiro 2024
**Versão da API:** 1.0
