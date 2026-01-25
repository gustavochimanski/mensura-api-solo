# Múltiplos meios de pagamento — Guia para frontend (Admin e Cliente)

O sistema aceita **mais de uma forma de pagamento por pedido**. Este documento descreve como os frontends **admin** e **cliente** devem implementar essa funcionalidade.

---

## 1. Visão geral

- Cada pedido pode ter **um ou mais** meios de pagamento.
- Cada meio possui um **valor** parcial; a **soma dos valores deve ser igual ao total do pedido**.
- Exemplos: R$ 50 em PIX + R$ 30 em dinheiro; ou 100% em cartão.

### Onde usar

| Contexto | Endpoint | Campo no payload |
|----------|----------|------------------|
| **Cliente – checkout (criar pedido)** | `POST /api/pedidos/client/checkout` | `meios_pagamento` |
| **Admin – atualizar pedido** | `PUT /api/pedidos/admin/{pedido_id}` | `pagamentos` |

### Onde obter a lista de meios

| Contexto | Endpoint | Autenticação |
|----------|----------|--------------|
| **Cliente (loja)** | `GET /api/cadastros/client/meios-pagamento` | Super-token (cliente) |
| **Admin** | `GET /api/cadastros/admin/meios-pagamento` | Bearer (admin) |

Resposta: array de `MeioPagamentoResponse` (`id`, `nome`, `tipo`, `ativo`, `created_at`, `updated_at`). Use apenas meios com `ativo: true`.

---

## 2. Contrato de um item de pagamento

Cada elemento na lista é um objeto com:

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `id` | `number` | Sim* | ID do meio de pagamento (preferencial) |
| `meio_pagamento_id` | `number` | Sim* | **(Legado)** ID do meio; use `id` quando possível |
| `valor` | `number` | Sim | Valor pago por este meio (duas casas decimais) |

\* É obrigatório informar **ou** `id` **ou** `meio_pagamento_id`.

Exemplo:

```json
{
  "id": 2,
  "valor": 45.90
}
```

Ou, legado:

```json
{
  "meio_pagamento_id": 2,
  "valor": 45.90
}
```

---

## 3. Cliente – Checkout (criar pedido)

### Endpoint

- **POST** `/api/pedidos/client/checkout`
- **Body:** `FinalizarPedidoRequest` (JSON).
- **Autenticação:** Super-token do cliente (header ou cookie, conforme sua API).

### Campo `meios_pagamento`

- **Tipo:** `array` de `{ id, valor }` (ou `meio_pagamento_id` no legado).
- **Obrigatório:** Sim, para finalizar o pedido.
- **Regra:** A **soma** de todos os `valor` deve ser **igual ao valor_total** do pedido (após preview).

### Fluxo recomendado no frontend

1. Calcular o total do pedido (via `POST /api/pedidos/client/checkout/preview` ou sua lógica local).
2. Buscar meios ativos: `GET /api/cadastros/client/meios-pagamento`.
3. Na tela de pagamento:
   - Permitir escolher **um ou mais** meios.
   - Para cada meio, informar o **valor** (ex.: input numérico).
   - Validar: `soma dos valores === valor_total`.
4. Ao finalizar, enviar `meios_pagamento` no body do `POST /api/pedidos/client/checkout`.

### Exemplo com **um** meio

```json
{
  "empresa_id": 1,
  "tipo_pedido": "DELIVERY",
  "tipo_entrega": "DELIVERY",
  "endereco_id": 42,
  "meios_pagamento": [
    { "id": 1, "valor": 89.90 }
  ],
  "produtos": {
    "itens": [
      { "produto_cod_barras": "7891234567890", "quantidade": 2 }
    ],
    "receitas": [],
    "combos": []
  }
}
```

### Exemplo com **múltiplos** meios

```json
{
  "empresa_id": 1,
  "tipo_pedido": "DELIVERY",
  "tipo_entrega": "DELIVERY",
  "endereco_id": 42,
  "meios_pagamento": [
    { "id": 1, "valor": 50.00 },
    { "id": 2, "valor": 39.90 }
  ],
  "produtos": {
    "itens": [
      { "produto_cod_barras": "7891234567890", "quantidade": 2 }
    ],
    "receitas": [],
    "combos": []
  }
}
```

`50.00 + 39.90 = 89.90` → deve ser o `valor_total` do pedido.

### Troco (`troco_para`)

- Quando houver pagamento em **dinheiro**, o frontend pode enviar `troco_para` (valor que o cliente vai dar).
- O backend valida `troco_para >= valor_total` para o(s) meio(s) em dinheiro.
- `troco_para` é opcional; use apenas se o meio for dinheiro.

### Comportamento do backend

- Se a **soma dos valores for menor** que o total, o backend **ajusta o valor do primeiro** meio para o total (comportamento de fallback). O frontend deve evitar isso e sempre enviar `soma === total`.

---

## 4. Admin – Atualizar pedido

### Endpoint

- **PUT** `/api/pedidos/admin/{pedido_id}`
- **Body:** JSON com campos opcionais, incluindo `pagamentos`.
- **Autenticação:** Bearer (admin).

### Campo `pagamentos`

- **Tipo:** `array` de `{ id, valor }` (ou `meio_pagamento_id`).
- **Obrigatório:** Não. Se enviado, **substitui** os meios de pagamento parciais do pedido.
- **Regra:** A soma dos `valor` deve igualar o `valor_total` do pedido.

### Exemplo de body (apenas pagamentos)

```json
{
  "pagamentos": [
    { "id": 1, "valor": 70.00 },
    { "id": 3, "valor": 19.90 }
  ]
}
```

### Exemplo completo (com outros campos)

```json
{
  "observacoes": "Cliente pediu troco para 100",
  "troco_para": 100.00,
  "pagamentos": [
    { "id": 2, "valor": 89.90 }
  ]
}
```

---

## 5. Respostas da API (pedido)

Os endpoints de pedido (GET por id, listagens, etc.) retornam, entre outros:

- `meio_pagamento_id`: ID do meio “principal” (compatibilidade; normalmente o primeiro).
- `pagamento`: resumo único (status, valor, meio, etc.). Em cenários com múltiplos meios, esse resumo pode representar apenas o principal.
- O backend persiste **todas** as transações por meio; futuras versões da API podem expor uma lista `transacoes` ou `meios_pagamento` na resposta.

Hoje, para **exibir** múltiplos meios na tela de detalhe do pedido, use o que a API já retornar (ex.: `pagamento`, `meio_pagamento_id`) e, se existir, `pagamentos_snapshot` ou estrutura equivalente documentada no CRUD de pedidos.

---

## 6. TypeScript – Tipos e exemplo

```typescript
interface MeioPagamentoParcial {
  id?: number;
  meio_pagamento_id?: number; // legado
  valor: number;
}

// Checkout (cliente)
interface CheckoutRequest {
  empresa_id: number;
  tipo_pedido: "DELIVERY" | "MESA" | "BALCAO";
  tipo_entrega: "DELIVERY" | "RETIRADA";
  endereco_id?: number;
  meios_pagamento: MeioPagamentoParcial[];
  produtos: { itens: any[]; receitas: any[]; combos: any[] };
  troco_para?: number;
  // ... outros campos
}

// Admin – atualizar pedido
interface PedidoUpdateRequest {
  pagamentos?: MeioPagamentoParcial[];
  observacoes?: string;
  troco_para?: number;
  // ... outros campos
}
```

### Exemplo de validação no frontend (cliente)

```typescript
function validarMeiosPagamento(
  meios: MeioPagamentoParcial[],
  valorTotal: number
): { ok: boolean; erro?: string } {
  if (!meios?.length) {
    return { ok: false, erro: "Selecione ao menos um meio de pagamento." };
  }
  const soma = meios.reduce((acc, m) => acc + m.valor, 0);
  const diff = Math.abs(soma - valorTotal);
  if (diff > 0.01) {
    return {
      ok: false,
      erro: `Soma dos pagamentos (R$ ${soma.toFixed(2)}) deve ser igual ao total (R$ ${valorTotal.toFixed(2)}).`,
    };
  }
  return { ok: true };
}
```

---

## 7. Checklist de implementação

### Cliente (checkout)

- [ ] Buscar meios ativos em `GET /api/cadastros/client/meios-pagamento`.
- [ ] Na tela de pagamento, permitir selecionar **um ou mais** meios e informar **valor** por meio.
- [ ] Validar `soma(valores) === valor_total` antes de enviar.
- [ ] Enviar `meios_pagamento` no `POST /api/pedidos/client/checkout`.
- [ ] Se houver dinheiro, enviar `troco_para` quando aplicável.

### Admin

- [ ] Buscar meios ativos em `GET /api/cadastros/admin/meios-pagamento`.
- [ ] Na edição do pedido, permitir alterar **pagamentos** (lista de `{ id, valor }`).
- [ ] Garantir `soma(valores) === valor_total` ao enviar `pagamentos` no `PUT /api/pedidos/admin/{id}`.
- [ ] Exibir os meios/valores do pedido na tela de detalhes conforme retornado pela API.

### Geral

- [ ] Usar `id` (evitar `meio_pagamento_id` legado) quando possível.
- [ ] Tratar erros 400 (meio inválido/inativo, totais não batendo, etc.).
- [ ] Opcional: integrar com WebSocket `meios_pagamento.v1.atualizados` para atualizar a lista de meios em tempo real (ver `DOCUMENTACAO_MEIOS_PAGAMENTO_WEBSOCKET.md`).

---

## 8. Referências

- **CRUD de pedidos:** `app/api/pedidos/DOCUMENTACAO_CRUD_PEDIDOS.md`
- **WebSocket – meios de pagamento:** `app/api/notifications/docs/DOCUMENTACAO_MEIOS_PAGAMENTO_WEBSOCKET.md`
- **Schemas:** `MeioPagamentoParcialRequest`, `FinalizarPedidoRequest`, `PedidoUpdateRequest`

---

**Última atualização:** 2026-01-24
