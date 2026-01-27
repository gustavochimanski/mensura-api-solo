# Documentação - Clonar Complementos (Frontend)

Endpoint para **clonar os acompanhamentos (complementos)** de um produto, receita ou combo para outro item do mesmo tipo ou de tipo diferente.

---

## 📋 Índice

1. [Base URL e autenticação](#base-url-e-autenticação)
2. [Estrutura de dados](#estrutura-de-dados)
3. [Endpoint](#endpoint)
4. [Regras e validações](#regras-e-validações)
5. [Códigos de status e erros](#códigos-de-status-e-erros)
6. [Exemplos](#exemplos)

---

## 🔐 Base URL e autenticação

### Base URL

**Prefixo**: `POST /api/catalogo/admin/complementos/clonar`

**Exemplos:**
- **Local**: `http://localhost:8000/api/catalogo/admin/complementos/clonar`
- **Produção**: `https://seu-dominio.com/api/catalogo/admin/complementos/clonar`

### Autenticação

Requer autenticação de **administrador** (`get_current_user`), com token JWT no header:

```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

---

## 📊 Estrutura de dados

### Request (body JSON)

| Campo                | Tipo     | Obrigatório | Descrição |
|----------------------|----------|-------------|-----------|
| `tipo_origem`        | string   | Sim         | Tipo do item de origem: `"produto"`, `"receita"` ou `"combo"` |
| `identificador_origem` | string ou number | Sim | Código de barras (produto) ou ID (receita/combo). Para receita/combo pode ser enviado como número. |
| `tipo_destino`       | string   | Sim         | Tipo do item de destino: `"produto"`, `"receita"` ou `"combo"` |
| `identificador_destino` | string ou number | Sim | Código de barras (produto) ou ID (receita/combo). Para receita/combo pode ser enviado como número. |

**Tipos TypeScript:**

```typescript
type TipoItem = "produto" | "receita" | "combo";

interface ClonarComplementosRequest {
  tipo_origem: TipoItem;
  identificador_origem: string | number;  // string = cod_barras (produto), number = id (receita/combo)
  tipo_destino: TipoItem;
  identificador_destino: string | number;
}
```

### Response (sucesso 200)

| Campo                 | Tipo   | Descrição |
|-----------------------|--------|-----------|
| `tipo_origem`         | string | Tipo do item de origem |
| `identificador_origem` | string \| number | Identificador usado na origem |
| `tipo_destino`        | string | Tipo do item de destino |
| `identificador_destino` | string \| number | Identificador usado no destino |
| `complementos_clonados` | number | Quantidade de complementos copiados |
| `mensagem`            | string | Mensagem descritiva do resultado |

**Exemplo de resposta:**

```json
{
  "tipo_origem": "receita",
  "identificador_origem": 5,
  "tipo_destino": "receita",
  "identificador_destino": 12,
  "complementos_clonados": 3,
  "mensagem": "3 complemento(s) clonado(s) com sucesso."
}
```

**Tipos TypeScript:**

```typescript
interface ClonarComplementosResponse {
  tipo_origem: string;
  identificador_origem: string | number;
  tipo_destino: string;
  identificador_destino: string | number;
  complementos_clonados: number;
  mensagem: string;
}
```

---

## 🚀 Endpoint

### POST /api/catalogo/admin/complementos/clonar

Copia **todos os complementos** do item de origem para o item de destino, preservando por complemento:

- ordem de exibição  
- obrigatório  
- quantitativo  
- mínimo/máximo de itens  

Os complementos já vinculados ao destino são **substituídos** pela lista clonada (não é merge).

**Comportamento:**

- Se o item de origem não tiver complementos, retorna `complementos_clonados: 0` e mensagem informativa (sucesso 200).
- Origem e destino podem ser de tipos diferentes (ex.: clonar de receita para combo).
- Para **produto**, use sempre string em `identificador` (código de barras).
- Para **receita** e **combo**, use o ID numérico (pode ser enviado como número ou string numérica).

---

## ✅ Regras e validações

1. **Mesmo item**: Se origem e destino forem o mesmo (mesmo tipo e mesmo identificador), a API retorna **400** com detalhe: `"Não é possível clonar complementos para o mesmo item."`

2. **Item de origem inexistente**: Se o item de origem não existir, a listagem de complementos retorna vazia e a resposta é sucesso com `complementos_clonados: 0` e mensagem `"Nenhum complemento vinculado ao item de origem."` (não é 404).

3. **Item de destino inexistente**: Ao vincular no destino, o backend valida existência do produto/receita/combo. Se o destino não existir, a API retorna **404** com detalhe apropriado (ex.: `"Produto X não encontrado."`, `"Receita Y não encontrada."`, etc.).

4. **Empresa**: Produto, receita, combo e complementos devem pertencer à mesma empresa; regras de negócio dos endpoints de vinculação continuam valendo.

---

## 🔢 Códigos de status e erros

| Status | Significado |
|--------|-------------|
| **200** | Sucesso. Complementos clonados (ou zero se origem sem complementos). |
| **400** | Origem e destino são o mesmo item. |
| **404** | Item de destino não encontrado (produto/receita/combo). |
| **422** | Erro de validação do body (tipos/identificadores inválidos). |

**Exemplo de erro 400:**

```json
{
  "detail": "Não é possível clonar complementos para o mesmo item."
}
```

**Exemplo de erro 404 (destino não encontrado):**

```json
{
  "detail": "Receita 999 não encontrada."
}
```

---

## 📌 Exemplos

### 1. Clonar complementos de uma receita para outra (receita → receita)

**Request:**

```http
POST /api/catalogo/admin/complementos/clonar
Content-Type: application/json
Authorization: Bearer {token}

{
  "tipo_origem": "receita",
  "identificador_origem": 5,
  "tipo_destino": "receita",
  "identificador_destino": 12
}
```

**Response 200:**

```json
{
  "tipo_origem": "receita",
  "identificador_origem": 5,
  "tipo_destino": "receita",
  "identificador_destino": 12,
  "complementos_clonados": 3,
  "mensagem": "3 complemento(s) clonado(s) com sucesso."
}
```

### 2. Clonar complementos de uma receita para um combo (receita → combo)

**Request:**

```http
POST /api/catalogo/admin/complementos/clonar
Content-Type: application/json
Authorization: Bearer {token}

{
  "tipo_origem": "receita",
  "identificador_origem": 3,
  "tipo_destino": "combo",
  "identificador_destino": 7
}
```

### 3. Clonar complementos de um produto para outro (produto → produto)

**Request:**

```http
POST /api/catalogo/admin/complementos/clonar
Content-Type: application/json
Authorization: Bearer {token}

{
  "tipo_origem": "produto",
  "identificador_origem": "7891234567890",
  "tipo_destino": "produto",
  "identificador_destino": "7891234567891"
}
```

### 4. Uso no frontend (fetch / axios)

```typescript
async function clonarComplementos(
  tipoOrigem: "produto" | "receita" | "combo",
  identificadorOrigem: string | number,
  tipoDestino: "produto" | "receita" | "combo",
  identificadorDestino: string | number,
  token: string
): Promise<ClonarComplementosResponse> {
  const res = await fetch("/api/catalogo/admin/complementos/clonar", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      tipo_origem: tipoOrigem,
      identificador_origem: identificadorOrigem,
      tipo_destino: tipoDestino,
      identificador_destino: identificadorDestino,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}
```

---

## Resumo rápido

| Item | Valor |
|------|--------|
| **Método** | `POST` |
| **URL** | `/api/catalogo/admin/complementos/clonar` |
| **Auth** | `Authorization: Bearer {admin_token}` |
| **Body** | `ClonarComplementosRequest` (JSON) |
| **Resposta** | `ClonarComplementosResponse` (200) |
| **Efeito** | Substitui os complementos do destino pelos da origem, mantendo ordem e configurações (obrigatório, quantitativo, min/max itens). |
