# Plano de Integração iFood – Mensura API

Documento com o que é necessário para integrar o iFood ao backend Mensura: requisitos, alterações no sistema, APIs do iFood e etapas de implementação.

---

## 1. Visão geral

- **Objetivo:** Receber pedidos do iFood na Mensura, criar/atualizar pedidos de delivery com canal `IFOOD`, confirmar/cancelar no iFood e manter status sincronizado.
- **Módulo sugerido:** `app/api/ifood/`
- **Documentação iFood:** [developer.ifood.com.br](https://developer.ifood.com.br) (Merchant, Order, Events, Authentication).

---

## 2. Requisitos do iFood (obrigatórios)

Para a loja aparecer e receber pedidos:

| Requisito | Descrição |
|-----------|-----------|
| **Presença** | Polling em `GET /events:polling` a cada **30 segundos** (ou webhook configurado). Sem isso, a loja cai. |
| **Confirmação** | Confirmar pedidos (PLC → CFM) dentro do prazo. |
| **ACK de eventos** | Enviar `POST /events/acknowledgment` para **todos** os eventos recebidos (mesmo os ignorados). |
| **Catálogo** | Pelo menos um cardápio habilitado no iFood. |
| **Área de entrega** | Configurada no iFood. |
| **Horário** | Dentro do horário de funcionamento. |
| **Interrupções** | Sem interrupções vigentes. |

**Homologação:** usar conta **Profissional (CNPJ)**. Conta CPF não é aceita.

---

## 3. Autenticação iFood (OAuth 2.0)

| Item | Detalhe |
|------|---------|
| **Fluxo** | OAuth 2.0 com client credentials (ou fluxo do app centralizado/distribuído conforme o modelo do iFood). |
| **Tokens** | Access token (Bearer) + refresh token. |
| **Validade** | Access: **3 horas**; Refresh: **168 horas** (7 dias). |
| **Uso** | Header `Authorization: Bearer {access_token}` em todas as chamadas. |
| **Refresh** | Renovar access token antes de expirar usando o refresh token. |

**Onde obter:** Credenciais (Client ID, Client Secret) no [Portal iFood Developer](https://developer.ifood.com.br). Cada empresa/merchant pode ter seu próprio token ou usar um app centralizado com múltiplos merchants.

---

## 4. Eventos de pedido (Order Events)

### 4.1 Entrega dos eventos

- **Polling:** `GET /events:polling` a cada 30s. Retorno 200 com lista de eventos ou 204 sem eventos.
- **Webhook:** iFood envia POST para uma URL configurada. Exige endpoint público, validação de assinatura e idempotência.

### 4.2 Grupos e códigos relevantes

| Grupo | Código | Nome | Ação na Mensura |
|-------|--------|------|------------------|
| **ORDER_STATUS** | PLC | PLACED | Novo pedido → buscar detalhes → criar pedido delivery, canal IFOOD → confirmar no iFood. |
| | CFM | CONFIRMED | Pedido confirmado (por nós ou outro device). Atualizar status para “em impressão/preparo” conforme seu fluxo. |
| | RTP | READY_TO_PICKUP | Pronto para retirada. Atualizar status se necessário. |
| | DSP | DISPATCHED | Saiu para entrega. Atualizar status “S” (saiu para entrega). |
| | CON | CONCLUDED | Pedido concluído. Atualizar status “E” (entregue). |
| | CAN | CANCELLED | Pedido cancelado. Atualizar status “C” (cancelado). |
| **CANCELLATION_REQUEST** | CAR | CANCELLATION_REQUESTED | Requisição de cancelamento (mercado ou iFood). Tratar e, se aceito, cancelar na Mensura e responder iFood. |
| | CCR | CONSUMER_CANCELLATION_REQUESTED | Cliente pediu cancelamento. Aceitar ou rejeitar via API. |
| | CCA | CONSUMER_CANCELLATION_ACCEPTED | Cancelamento do cliente aceito. |
| | CCD | CONSUMER_CANCELLATION_DENIED | Cancelamento do cliente negado. |
| **DELIVERY** | ADR, GTO, AAO, CLT, AAD, … | Atribuição de entregador, a caminho, coletado, etc. | Opcional: informar usuário/cozinha; não obrigatório para MVP. |
| **OTHER** | OPA | ORDER_PATCHED | Alteração no pedido (itens). Buscar detalhes e atualizar itens no pedido Mensura. |

**Importante:**

- Ordenar eventos por `createdAt`.
- Tratar eventos duplicados (mesmo `id`): processar apenas uma vez, mas **sempre** enviar ACK.
- Polling: usar header `x-polling-merchants` com lista de `merchantId` (até 100 por request) quando houver múltiplos estabelecimentos.

---

## 5. APIs iFood que você precisará usar

| Operação | Método | Endpoint (base: `https://merchant-api.ifood.com.br`) | Uso |
|----------|--------|------------------------------------------------------|-----|
| **Auth** | POST | `/authentication/v1.0/oauth/token` | Obter access + refresh token. |
| **Auth refresh** | POST | `/authentication/v1.0/oauth/token` (com refresh_token) | Renovar access token. |
| **Polling** | GET | `/order/v1.0/events:polling` | Buscar eventos (a cada 30s). |
| **ACK** | POST | `/order/v1.0/events/acknowledgment` | Confirmar eventos recebidos. |
| **Detalhes do pedido** | GET | `/order/v1.0/orders/{orderId}` | Ao receber PLC (e OPA), buscar itens, endereço, valores. |
| **Confirmar pedido** | POST | `/order/v1.0/orders/{orderId}/confirm` | Após criar pedido na Mensura, confirmar no iFood. |
| **Iniciar preparo** | POST | `/order/v1.0/orders/{orderId}/startPreparation` | Opcional; seguir fluxo da doc. |
| **Pedido pronto** | POST | `/order/v1.0/orders/{orderId}/readyToPickup` | Quando estiver pronto para retirada/entrega. |
| **Despachar** | POST | `/order/v1.0/orders/{orderId}/dispatch` | Quando “saiu para entrega”. |
| **Cancelar** | POST | `/order/v1.0/orders/{orderId}/cancel` | Cancelar no iFood (código de motivo obrigatório). |
| **Listar merchants** | GET | `/merchant/v1.0/merchants` | Listar lojas vinculadas ao token. |
| **Status da loja** | GET | `/merchant/v1.0/merchants/{merchantId}/status` | Ver se loja está OK, WARNING, CLOSED, ERROR. |
| **Interrupções** | GET/POST/DELETE | `/merchant/v1.0/merchants/{merchantId}/interruptions` | Fechar/reabrir loja. |

*(Valide os paths exatos na [Referência de APIs](https://developer.ifood.com.br/en-US/docs/references) do iFood.)*

---

## 6. Alterações no sistema Mensura

### 6.1 Enums e banco

| Onde | O que fazer |
|------|-------------|
| **`CanalPedido`** (`model_pedido_unificado`) | Incluir `IFOOD = "IFOOD"`. |
| **`OrigemPedidoEnum`** (`schema_shared_enums`) | Incluir `IFOOD = "IFOOD"`. |
| **PostgreSQL** | Adicionar `'IFOOD'` ao enum `pedidos.canal_pedido_enum` (`ALTER TYPE ... ADD VALUE 'IFOOD'`). |
| **`cardapio.origem_pedido_enum`** (se usado para origem) | Incluir `IFOOD` se aplicável. |

### 6.2 Novas tabelas

**a) Configuração Empresa–iFood**

Exemplo: `cadastros.empresas_ifood_config` (ou `ifood.config_empresa`).

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL PK | |
| `empresa_id` | INT FK → cadastros.empresas | Empresa Mensura. |
| `ifood_merchant_id` | UUID | ID do merchant no iFood. |
| `client_id` | VARCHAR | Client ID OAuth (criptografado se possível). |
| `client_secret` | VARCHAR | Client secret (criptografado). |
| `access_token` | TEXT | Access token atual. |
| `refresh_token` | TEXT | Refresh token. |
| `token_expires_at` | TIMESTAMPTZ | Expiração do access token. |
| `ativo` | BOOLEAN | Se a integração está ativa. |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

**Restrição:** `UNIQUE(empresa_id)` (uma config por empresa).

**b) Vínculo Pedido ↔ iFood**

Exemplo: `pedidos.pedidos_ifood`.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL PK | |
| `pedido_id` | INT FK → pedidos.pedidos | Pedido Mensura. |
| `ifood_order_id` | UUID | ID do pedido no iFood. |
| `ifood_merchant_id` | UUID | Merchant do pedido. |
| `created_at` | TIMESTAMPTZ | |

**Restrição:** `UNIQUE(ifood_order_id)` (evitar duplicar por evento duplicado).

### 6.3 Mapeamento iFood → Mensura

| Conceito iFood | Na Mensura |
|----------------|------------|
| Merchant | `empresa_id` (via `empresas_ifood_config`). |
| Order (orderId) | `pedidos` + `pedidos_ifood.pedido_id` / `ifood_order_id`. |
| Itens (externalCode, etc.) | `pedidos_itens`: `produto_cod_barras` ou `receita_id` ou `combo_id`. |
| Endereço de entrega | `endereco_snapshot` (JSON) e, se houver, `endereco_geo`. |
| Tipo entrega | Sempre `DELIVERY` para pedidos iFood. |
| Canal/origem | `IFOOD`. |
| Status | Mapear PLC→criar; CFM/RTP/DSP/CON/CAN→atualizar status do pedido (P, I, R, S, E, C). |

**Itens:** O iFood envia `externalCode` (ou similar) por item. É necessário mapear para:

- `produto_cod_barras`, ou  
- `receita_id`, ou  
- `combo_id`  

Isso exige **mapeamento catálogo iFood ↔ catálogo Mensura** (tabela de mapeamento ou convenção de códigos, ex.: `externalCode` = `cod_barras` ou `"RECEITA-{id}"` / `"COMBO-{id}"`).

---

## 7. Fluxo de dados resumido

### 7.1 Novo pedido (PLC)

1. Receber evento PLC (polling ou webhook).
2. Buscar detalhes: `GET /orders/{orderId}`.
3. Resolver `merchantId` → `empresa_id` (config iFood).
4. Verificar se já existe `pedidos_ifood` com esse `orderId`; se sim, só fazer ACK e ignorar.
5. Criar pedido em `pedidos` (delivery, canal IFOOD, `endereco_snapshot` com endereço iFood).
6. Criar itens em `pedidos_itens` (usando mapeamento externalCode → produto/receita/combo).
7. Inserir em `pedidos_ifood` (`pedido_id`, `ifood_order_id`, `ifood_merchant_id`).
8. Chamar `POST /orders/{orderId}/confirm` no iFood.
9. Enviar ACK do evento.

### 7.2 Atualizações de status (CFM, RTP, DSP, CON, CAN)

1. Receber evento.
2. Buscar `pedido_id` em `pedidos_ifood` por `ifood_order_id`.
3. Atualizar status do pedido na Mensura conforme a tabela de eventos (seção 4.2).
4. Enviar ACK.

### 7.3 Alteração de itens (OPA)

1. Receber OPA.
2. Buscar detalhes atualizados do pedido.
3. Ajustar itens do pedido na Mensura (conforme regras de negócio: substituir, recalcular totais, etc.).
4. Enviar ACK.

### 7.4 Quando a cozinha/operador muda status na Mensura

- **“Saiu para entrega”** → chamar `POST /orders/{orderId}/dispatch` no iFood.
- **Cancelar** → chamar `POST /orders/{orderId}/cancel` com motivo válido.

*(Outros status, como “pronto para retirada”, conforme fluxo desejado e APIs acima.)*

---

## 8. Estrutura sugerida do módulo `app/api/ifood/`

```
app/api/ifood/
├── __init__.py
├── docs/
│   └── PLANO_INTEGRACAO_IFOOD.md   (este plano)
├── models/
│   ├── __init__.py
│   ├── model_empresa_ifood_config.py
│   └── model_pedido_ifood.py
├── repositories/
│   ├── __init__.py
│   ├── repo_ifood_config.py
│   └── repo_pedido_ifood.py
├── services/
│   ├── __init__.py
│   ├── ifood_auth_service.py      # OAuth token + refresh
│   ├── ifood_api_client.py        # HTTP: orders, events, confirm, cancel
│   ├── ifood_event_processor.py   # PLC, CFM, DSP, CON, CAN, OPA, etc.
│   └── ifood_order_sync_service.py # iFood order → Pedido + itens
├── router/
│   ├── __init__.py
│   └── router_ifood_admin.py      # CRUD config, iniciar polling, etc.
├── schemas/
│   ├── __init__.py
│   └── schema_ifood_config.py
└── worker/
    └── ifood_polling_worker.py    # Loop polling 30s + processar eventos
```

- **Config:** Salvar em `empresas_ifood_config`; tokens em memória ou em tabela (com cuidado de segurança).
- **Worker:** Pode ser um processo separado, Celery, ou background task (FastAPI), desde que respeite o intervalo de 30s e use `x-polling-merchants` quando houver vários merchants.

---

## 9. Configuração e variáveis de ambiente

Sugestão:

| Variável | Descrição |
|----------|-----------|
| `IFOOD_API_BASE_URL` | Base da Merchant API (ex.: `https://merchant-api.ifood.com.br`). |
| `IFOOD_AUTH_URL` | URL de autenticação (pode ser a mesma base + path OAuth). |
| `IFOOD_POLLING_ENABLED` | `true`/`false` para ativar/desativar polling. |
| `IFOOD_POLLING_INTERVAL_SEC` | Intervalo em segundos (recomendado: 30). |

Credenciais por empresa ficam em `empresas_ifood_config`, não em env global (exceto se usar um único app iFood para todas).

---

## 10. Segurança

- Não versionar `client_secret` nem tokens. Preferir variáveis de ambiente ou cofre (ex.: AWS Secrets Manager, Vault).
- Se guardar em banco: criptografar `client_secret`, `access_token`, `refresh_token`.
- Webhook: validar assinatura dos requests conforme [documentação iFood](https://developer.ifood.com.br/en-US/docs/guides/modules/events/webhook-overview).
- Restringir rotas admin de configuração iFood a usuários autorizados (mesmo esquema de auth do restante do admin).

---

## 11. Homologação iFood

- Conta **CNPJ**.
- App funcionando de ponta a ponta: receber PLC → criar pedido → confirmar → receber CFM/DSP/CON.
- Polling estável a cada 30s ou webhook configurado e operando.
- ACK em todos os eventos.
- Uso de `x-polling-merchants` quando múltiplos merchants.
- Pedidos de teste: [Generate test orders](https://developer.ifood.com.br/en-US/docs/getting-started/first-steps/generate-test-order).

---

## 12. Ordem sugerida de implementação

1. **Enums e BD:** Adicionar `IFOOD` aos enums; criar `empresas_ifood_config` e `pedidos_ifood`; migrar ou rodar `init_db` conforme o padrão do projeto.
2. **Auth:** Serviço de OAuth (obter e renovar token); salvar/recuperar tokens por empresa.
3. **Cliente HTTP:** Implementar chamadas à API iFood (orders, events, confirm, cancel, etc.).
4. **Processador de eventos:** Tratar PLC → criar pedido + itens, gravar `pedidos_ifood`, confirmar no iFood; depois CFM, DSP, CON, CAN, OPA.
5. **Polling (ou webhook):** Worker de polling 30s + ACK; ou endpoint de webhook + validação de assinatura.
6. **Router admin:** CRUD de config iFood por empresa; endpoints para disparar polling manualmente ou ver status.
7. **Mapeamento de catálogo:** Definir regra externalCode → produto/receita/combo; implementar e testar com itens reais.
8. **Sincronização reversa:** Ao mudar status na Mensura (ex.: “saiu para entrega”, cancelar), chamar APIs correspondentes do iFood.
9. **Testes e homologação:** Pedidos de teste, cenários de cancelamento, e checklist da documentação iFood.

---

## 13. Referências rápidas

- [iFood Developer – Merchant](https://developer.ifood.com.br/en-US/docs/guides/merchant/workflow/)
- [iFood Developer – Order events](https://developer.ifood.com.br/en-US/docs/guides/modules/order/events)
- [iFood Developer – Event polling](https://developer.ifood.com.br/en-US/docs/guides/modules/events/polling-overview)
- [iFood Developer – Authentication](https://developer.ifood.com.br/en-US/docs/guides/authentication/)
- [API Reference](https://developer.ifood.com.br/en-US/docs/references)
- [Generate test orders](https://developer.ifood.com.br/en-US/docs/getting-started/first-steps/generate-test-order)

---

*Documento gerado como plano de integração. Implementação deve seguir a arquitetura e padrões do projeto Mensura.*
