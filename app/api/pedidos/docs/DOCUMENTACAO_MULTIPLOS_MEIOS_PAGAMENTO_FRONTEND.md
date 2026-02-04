# Múltiplos Meios de Pagamento por Pedido (Frontend)

Esta documentação descreve **como o frontend deve enviar e consumir** pagamentos quando um pedido pode ter **uma ou mais transações** (ex.: parte em PIX_ONLINE, parte em dinheiro).

## 1) Conceitos / Fonte da verdade

- **Pedido** (`pedidos.pedidos`): pode ter **0..N transações** de pagamento.
- **Transação de pagamento** (`cardapio.transacoes_pagamento_dv`): registra **um** meio de pagamento + **um valor** + **um status**.
- **Fonte da verdade para múltiplos pagamentos**: `pedido.transacoes[]`
- **Campo legado/atalho**: `pedido.meio_pagamento_id` e `pedido.transacao` (singular) existem por compatibilidade, mas **não representam múltiplas formas**.

## 2) Estados de pagamento e “pagar depois”

Uma transação pode ficar **`PENDENTE`** para ser paga/confirmada depois.

- **No checkout**: o backend cria transações com `status="PENDENTE"`.
- **Meios offline** (ex.: `DINHEIRO`, `CREDITO` na entrega, etc.): normalmente permanecem `PENDENTE` até um operador confirmar (admin/fechamento de conta).
- **PIX_ONLINE**: a transação pode continuar `PENDENTE` até o webhook do gateway confirmar `PAGO`/`AUTORIZADO`.

## 3) Checkout (criação do pedido) — payload

Ao finalizar o pedido, envie `meios_pagamento` como uma lista. Cada item tem:

- `id` (preferencial) **ou** `meio_pagamento_id` (legado)
- `valor` (valor parcial daquela forma)

Exemplo:

```json
{
  "tipo_pedido": "DELIVERY",
  "endereco_id": 10,
  "produtos": { "itens": [ { "produto_cod_barras": "789", "quantidade": 1 } ] },
  "meios_pagamento": [
    { "id": 1, "valor": 50.00 },
    { "id": 2, "valor": 25.00 }
  ]
}
```

## 4) Resposta do pedido — o que o frontend deve ler

Os endpoints de pedido passam a expor **`transacoes`**:

- `transacoes`: lista de transações do pedido (cada item é um `TransacaoResponse`)
- `transacao`: campo singular (legado). Pode existir, mas **não use** para múltiplos pagamentos.

Campos importantes em `transacoes[]`:

- `id`: **transacao_id** (use para iniciar pagamento no gateway / atualizar status no admin)
- `pedido_id`
- `meio_pagamento_id`
- `metodo`, `gateway`
- `valor`
- `status`: `PENDENTE | AUTORIZADO | PAGO | ...`
- `provider_transaction_id`, `qr_code`, `qr_code_base64` (quando aplicável)

## 5) Iniciar pagamento (PIX_ONLINE) — novo endpoint por transação

Quando existir mais de uma transação, o início do pagamento deve ser feito por **transação**.

### 5.1) Cliente (novo)

- **POST** `/api/cardapio/client/pagamentos/transacoes/{transacao_id}/iniciar`
- **Query**: `metodo=PIX_ONLINE` (default), `gateway=MERCADOPAGO` (default)
- **Resposta**: `TransacaoResponse` (com `qr_code`/`qr_code_base64` se o gateway retornar)

### 5.2) Cliente (legado)

- **POST** `/api/cardapio/client/pagamentos/{pedido_id}`
  - Se o pedido **não tem transações**, ainda pode criar/iniciar uma transação (legado).
  - Se o pedido tem **1 transação**, o backend reutiliza ela (não duplica).
  - Se o pedido tem **>1 transação**, retorna **409** pedindo para usar o endpoint por `transacao_id`.

## 6) Atualizar status (admin/webhook)

### 6.1) Admin (novo — recomendado)

- **POST** `/api/cardapio/admin/pagamentos/transacoes/{transacao_id}/status`
- Body: `TransacaoStatusUpdateRequest`

### 6.2) Admin (legado)

- **POST** `/api/cardapio/admin/pagamentos/{pedido_id}/status`
  - Se o pedido tiver **>1 transação**, retorna **409** (ambíguo).

### 6.3) Webhook (interno)

O webhook do Mercado Pago atualiza a transação pelo `provider_transaction_id` (não exige mudanças no front).

## 7) Regras práticas para o frontend

- **Sempre renderize pagamentos usando `pedido.transacoes[]`.**
- Para iniciar PIX_ONLINE, selecione uma transação `PENDENTE` com `metodo=PIX_ONLINE` e chame o endpoint por `transacao_id`.
- Para “pagar depois”, apenas mantenha a transação `PENDENTE` e permita que o admin confirme posteriormente.

