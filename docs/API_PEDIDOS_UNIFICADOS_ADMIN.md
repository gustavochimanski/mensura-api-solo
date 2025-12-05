# API de Pedidos Unificados (Admin)

## 1. Objetivo

Padronizar as operações de pedidos para o canal admin em um único conjunto de rotas REST, eliminando a duplicidade por tipo (`delivery`, `mesa`, `balcão`) e oferecendo um contrato consistente para o frontend.

## 2. Convenções Gerais

- **Prefixo base:** `/api/pedidos/admin`.
- **Autenticação:** mesmas dependências atuais (`Depends(get_current_user)`), mantidas via router.
- **Identificação do pedido:** `pedido_id` (inteiro). A inferência do tipo de pedido (`tipo_pedido`) é automática a partir dos dados persistidos.
- **Enums e Schemas reutilizados:** Manter `PedidoResponse`, `PedidoResponseCompleto`, `PedidoStatusEnum`, `ItemPedidoEditar`, etc., adicionando novos DTOs apenas quando necessário.
- **Respostas de mutação:** Sempre retornam `200 OK` com o pedido atualizado (`PedidoResponse` ou `PedidoResponseCompleto`, conforme contexto).
- **Tratamento de erros:** `404` quando o pedido não existe, `400` para validações de domínio, `403` para permissões.

## 3. Endpoints

### 3.1 Listagem e Consulta

| Método | Caminho | Descrição | Notas |
| --- | --- | --- | --- |
| GET | `/api/pedidos/admin` | Lista pedidos com filtros por tipo, status, intervalo de datas, mesa, cliente e empresa. | Combina rotas `/delivery`, `/mesa` e filtros específicos. Retorno paginado em `PedidoResponse`. |
| GET | `/api/pedidos/admin/kanban` | Recupera visão agregada para Kanban. | Parâmetros atuais (`date_filter`, `empresa_id`, `limit`) preservados. Retorna `KanbanAgrupadoResponse`. |
| GET | `/api/pedidos/admin/{pedido_id}` | Retorna detalhes completos do pedido. | Responde `PedidoResponseCompletoTotal`. |
| GET | `/api/pedidos/admin/{pedido_id}/historico` | Histórico de status e eventos. | Mesmo comportamento atual (`HistoricoDoPedidoResponse`). |

### 3.2 Criação

| Método | Caminho | Body | Descrição |
| --- | --- | --- | --- |
| POST | `/api/pedidos/admin` | `PedidoCreateRequest` | Cria pedido para qualquer tipo. Campo `tipo_pedido` (`DELIVERY`, `MESA`, `BALCAO`) orienta validações. Reaproveita estruturas existentes (`FinalizarPedidoRequest`, `PedidoMesaCreate`, `PedidoBalcaoCreate`) via composição. Resposta `PedidoResponseCompleto`. |

### 3.3 Atualizações Gerais

| Método | Caminho | Body | Descrição |
| --- | --- | --- | --- |
| PUT | `/api/pedidos/admin/{pedido_id}` | `PedidoUpdateRequest` | Atualização parcial de metadados comuns (cliente, pagamentos, observação geral, endereço/troco para delivery, mesa ligada, etc.). |
| PATCH | `/api/pedidos/admin/{pedido_id}/status` | `PedidoStatusPatchRequest` | Atualiza status (enum unificado). |
| PATCH | `/api/pedidos/admin/{pedido_id}/observacoes` | `PedidoObservacaoPatchRequest` | Atualiza observações gerais. |
| PATCH | `/api/pedidos/admin/{pedido_id}/fechar-conta` | `PedidoFecharContaRequest` (campos opcionais) | Garante fechamento unificado, delegando regras específicas por tipo. Retorna pedido atualizado. |
| PATCH | `/api/pedidos/admin/{pedido_id}/reabrir` | (sem body) | Reabre pedidos finalizados/cancelados (quando permitido). |
| DELETE | `/api/pedidos/admin/{pedido_id}` | — | Cancela pedido (status `CANCELADO`). |

### 3.4 Itens do Pedido

| Método | Caminho | Body | Descrição |
| --- | --- | --- | --- |
| POST | `/api/pedidos/admin/{pedido_id}/itens` | `PedidoItemMutationRequest` | Executa ações sobre itens (`ADD`, `UPDATE`, `REMOVE`). Estrutura baseada em `ItemPedidoEditar`, enriquecida com identificadores auxiliares. |
| PATCH | `/api/pedidos/admin/{pedido_id}/itens/{item_id}` | `PedidoItemMutationRequest` (com ação `UPDATE`) | Atalho para atualizar item específico. |
| DELETE | `/api/pedidos/admin/{pedido_id}/itens/{item_id}` | — | Remove item sem payload adicional. |

### 3.5 Entregador / Logística

| Método | Caminho | Body | Descrição |
| --- | --- | --- | --- |
| PUT | `/api/pedidos/admin/{pedido_id}/entregador` | `PedidoEntregadorRequest` | Vincula ou atualiza entregador (tipo delivery). |
| DELETE | `/api/pedidos/admin/{pedido_id}/entregador` | — | Remove entregador. |

### 3.6 Recursos Específicos de Mesa

Para manter compatibilidade com funcionalidades específicas de mesa (ex.: comandas, produtos genéricos), os endpoints genéricos de itens permanecem, com extensão via payload:

- `PedidoItemMutationRequest` aceita campos como `produto_cod_barras`, `receita_id`, `combo_id`, `adicionais` e `adicionais_ids`.
- O service centralizado delegará para estratégias de delivery/mesa/balcão, reutilizando `PedidoMesaService` internamente.

## 4. Schemas Propostos

### 4.1 PedidoCreateRequest

```json
{
  "tipo_pedido": "DELIVERY|MESA|BALCAO",
  "empresa_id": 123,
  "cliente_id": 456,
  "origem": "WEB|APP|PDV",
  "dados_delivery": {
    "endereco_id": 789,
    "troco_para": 100.0
  },
  "dados_mesa": {
    "mesa_id": 10,
    "num_pessoas": 4
  },
  "itens": [
    {
      "produto_cod_barras": "123",
      "quantidade": 1,
      "observacao": "..."
    }
  ],
  "pagamentos": [
    {
      "meio_pagamento_id": 1,
      "valor": 50.0
    }
  ],
  "observacao_geral": "string"
}
```

### 4.2 PedidoUpdateRequest (parcial)

```json
{
  "cliente_id": 456,
  "observacao_geral": "string",
  "pagamentos": [...],
  "dados_delivery": {...},
  "dados_mesa": {...}
}
```

### 4.3 PedidoItemMutationRequest

```json
{
  "acao": "ADD|UPDATE|REMOVE",
  "item_id": 1,
  "produto_cod_barras": "123",
  "receita_id": null,
  "combo_id": null,
  "quantidade": 2,
  "observacao": "sem cebola",
  "adicionais": [...],
  "adicionais_ids": [...]
}
```

### 4.4 PedidoEntregadorRequest

```json
{
  "entregador_id": 321
}
```

## 5. Estratégia de Implementação

1. **Service unificado (`PedidoAdminService`):** camada que orquestra operações comuns e delega comportamentos específicos (delivery/mesa/balcão) para serviços especializados já existentes.
2. **Router principal:** `app/api/pedidos/router/admin/router_pedidos_admin.py` expõe as rotas descritas acima.
3. **Schemas compartilhados:** adicionar novos DTOs em `app/api/pedidos/schemas`, reaproveitando classes atuais.
4. **Rollout:** uso de feature flags por empresa/ambiente para controlar adoção (vide plano de compatibilidade).

## 6. Compatibilidade Temporária

- Rotas legadas foram removidas; consumidores externos devem migrar para o contrato unificado descrito acima.
- Para referências históricas, utilize a tabela de equivalência em `docs/tabela_equivalencia_rotas_pedidos.md`.

## 7. Próximos Passos

1. Manter tabela de equivalência entre rotas antigas e o contrato unificado.
2. Atualizar testes e criar novos cenários cobrindo pedidos de todos os tipos.
3. Preparar/atualizar guia de migração para o frontend e integrações.

