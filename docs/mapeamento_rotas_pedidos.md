# Mapeamento de Rotas de Pedidos (Semana 1)

Este documento consolida as rotas atuais de pedidos por canal, com foco no diagnóstico inicial do plano de unificação.

## Admin – `app/api/pedidos/router/admin/router_pedidos_admin.py`

Prefixo base: `/api/pedidos/admin` (todas as rotas exigem `Depends(get_current_user)`).

### Bloco Geral

| Método | Caminho | Handler | Service principal | Notas |
| --- | --- | --- | --- | --- |
| GET | `/kanban` | `listar_pedidos_admin_kanban` | `PedidoService` (`list_all_kanban`) | Query obrigatória `date_filter`; filtros por empresa e limite. |
| GET | `/{pedido_id}` | `get_pedido` | `PedidoService` (`get_pedido_by_id_completo_total`) | Retorna `PedidoResponseCompletoTotal`; 404 quando não encontra. |
| GET | `/{pedido_id}/historico` | `obter_historico_pedido` | `PedidoService` + consulta direta ao modelo de histórico | Retorna `HistoricoDoPedidoResponse`; converte enums/manuais. |
| PUT | `/{pedido_id}/status` | `atualizar_status_pedido` | `PedidoService` (`atualizar_status`) | Query `novo_status`; valida existência e registra usuário. |
| DELETE | `/{pedido_id}` | `cancelar_pedido` | `PedidoService` (`atualizar_status` para `C`) | Cancela pedido para qualquer tipo (delivery/mesa/balcão). |

### Bloco Delivery

| Método | Caminho | Handler | Service principal | Notas |
| --- | --- | --- | --- | --- |
| POST | `/delivery` | `criar_pedido_delivery` | `PedidoService` (`finalizar_pedido`) | Requer `cliente_id`; payload `FinalizarPedidoRequest`; responde `PedidoResponse`. |
| GET | `/delivery` | `listar_pedidos_delivery` | `PedidoService` (`response_builder`) | Filtros opcionais (empresa, cliente, status, datas, paginação); consulta direta ao modelo unificado. |
| GET | `/delivery/cliente/{cliente_id}` | `listar_pedidos_delivery_por_cliente` | `PedidoService` (`listar_pedidos`) | Paginação (`skip/limit`); foco em pedidos do cliente. |
| PUT | `/delivery/{pedido_id}` | `atualizar_pedido_delivery` | `PedidoService` (`editar_pedido_parcial`) | Valida tipo `DELIVERY` antes de editar campos gerais. |
| PUT | `/delivery/{pedido_id}/itens` | `atualizar_itens_pedido_delivery` | `PedidoService` (`atualizar_item_pedido`) | Operações `adicionar/atualizar/remover`; valida tipo `DELIVERY`. |
| PUT | `/delivery/{pedido_id}/entregador` | `vincular_entregador_delivery` | `PedidoService` (`vincular_entregador`) | Query `entregador_id` opcional para (des)vincular; valida existência/tipo. |
| DELETE | `/delivery/{pedido_id}/entregador` | `desvincular_entregador_delivery` | `PedidoService` (`desvincular_entregador`) | Remove entregador de pedidos delivery. |

### Bloco Mesa

Todas dependem de `PedidoMesaService` via `get_mesa_service` (injeta contratos de produto/adicional/combo).

| Método | Caminho | Handler | Service principal | Notas |
| --- | --- | --- | --- | --- |
| POST | `/mesa` | `criar_pedido_mesa` | `PedidoMesaService` (`criar_pedido`) | Payload `PedidoMesaCreate`; cria pedido de mesa completo. |
| GET | `/mesa` | `listar_pedidos_mesa` | `PedidoMesaService` (`list_pedidos_abertos`) | Filtros `empresa_id` (obrigatório), `mesa_id`, `apenas_abertos`. |
| GET | `/mesa/{mesa_id}/finalizados` | `listar_pedidos_finalizados_mesa` | `PedidoMesaService` (`list_pedidos_finalizados`) | Filtro adicional `data_filtro`. |
| GET | `/mesa/cliente/{cliente_id}` | `listar_pedidos_mesa_por_cliente` | `PedidoMesaService` (`list_pedidos_by_cliente`) | Paginação (`skip/limit`) + filtro `empresa_id`. |
| PUT | `/mesa/{pedido_id}/adicionar-item` | `adicionar_item_pedido_mesa` | `PedidoMesaService` (`adicionar_item`) | Adiciona item com `AdicionarItemRequest`. |
| PUT | `/mesa/{pedido_id}/adicionar-produto-generico` | `adicionar_produto_generico_mesa` | `PedidoMesaService` (`adicionar_produto_generico`) | Suporta produtos, receitas e combos genéricos. |
| PUT | `/mesa/{pedido_id}/observacoes` | `atualizar_observacoes_pedido_mesa` | `PedidoMesaService` (`atualizar_observacoes`) | Atualiza observações gerais (payload `AtualizarObservacoesRequest`). |
| PUT | `/mesa/{pedido_id}/status` | `atualizar_status_pedido_mesa` | `PedidoMesaService` (`atualizar_status`) | Atualiza status específico de mesa. |
| PUT | `/mesa/{pedido_id}/fechar-conta` | `fechar_conta_mesa` | `PedidoMesaService` (`fechar_conta`) | Payload opcional `FecharContaMesaRequest`; trata pagamentos. |
| PUT | `/mesa/{pedido_id}/reabrir` | `reabrir_pedido_mesa` | `PedidoMesaService` (`reabrir`) | Reabre pedidos cancelados/finalizados. |
| DELETE | `/mesa/{pedido_id}/item/{item_id}` | `remover_item_pedido_mesa` | `PedidoMesaService` (`remover_item`) | Remove item específico da mesa. |

### Bloco Entregador (genérico)

| Método | Caminho | Handler | Service principal | Notas |
| --- | --- | --- | --- | --- |
| PUT | `/{pedido_id}/entregador` | `vincular_entregador` | `PedidoService` (`vincular_entregador`) | Versão genérica para qualquer pedido; aceita `entregador_id` opcional. |
| DELETE | `/{pedido_id}/entregador` | `desvincular_entregador` | `PedidoService` (`desvincular_entregador`) | Remove entregador; valida pedido existente. |

## Admin v2 – `app/api/pedidos/router/admin/router_pedidos_admin_v2.py`

Prefixo base: `/api/pedidos/admin/v2` (autenticado via `get_current_user`, orquestrado por `PedidoAdminService`).

| Método | Caminho | Handler | Service principal | Notas |
| --- | --- | --- | --- | --- |
| GET | `/` | `listar_pedidos_v2` | `PedidoAdminService.listar_pedidos` | Lista unificada com filtros por tipo, status, cliente, mesa e datas. |
| GET | `/kanban` | `listar_kanban_v2` | `PedidoAdminService.listar_kanban` | Mantém retorno `KanbanAgrupadoResponse`. |
| GET | `/{pedido_id}` | `obter_pedido_v2` | `PedidoAdminService.obter_pedido` | Retorna `PedidoResponseCompletoTotal`. |
| GET | `/{pedido_id}/historico` | `obter_historico_v2` | `PedidoAdminService.obter_historico` | Mesmo modelo de histórico atual. |
| POST | `/` | `criar_pedido_v2` | `PedidoAdminService.criar_pedido` | Payload `PedidoCreateRequest` (deriva de `FinalizarPedidoRequest`). |
| PUT | `/{pedido_id}` | `atualizar_pedido_v2` | `PedidoAdminService.atualizar_pedido` | Atualiza metadados comuns (cliente, pagamentos, observações). |
| PATCH | `/{pedido_id}/status` | `atualizar_status_v2` | `PedidoAdminService.atualizar_status` | Unifica mudança de status para todos os tipos. |
| DELETE | `/{pedido_id}` | `cancelar_pedido_v2` | `PedidoAdminService.cancelar` | Cancela pedido respeitando regras por tipo. |
| PATCH | `/{pedido_id}/observacoes` | `atualizar_observacoes_v2` | `PedidoAdminService.atualizar_observacoes` | Atualiza observações gerais (delivery) ou específicas (mesa/balcão). |
| PATCH | `/{pedido_id}/fechar-conta` | `fechar_conta_v2` | `PedidoAdminService.fechar_conta` | Apenas mesa/balcão (`PedidoFecharContaRequest`). |
| PATCH | `/{pedido_id}/reabrir` | `reabrir_pedido_v2` | `PedidoAdminService.reabrir` | Reabre pedidos considerando regras por tipo. |
| POST | `/{pedido_id}/itens` | `gerenciar_itens_v2` | `PedidoAdminService.gerenciar_item` | Ações `ADD/UPDATE/REMOVE` via `PedidoItemMutationRequest`. |
| PATCH | `/{pedido_id}/itens/{item_id}` | `atualizar_item_v2` | `PedidoAdminService.gerenciar_item` | Atualiza item específico (força ação `UPDATE`). |
| DELETE | `/{pedido_id}/itens/{item_id}` | `remover_item_v2` | `PedidoAdminService.remover_item` | Remove item de qualquer tipo de pedido. |
| PUT | `/{pedido_id}/entregador` | `atualizar_entregador_v2` | `PedidoAdminService.atualizar_entregador` | Vincula/desvincula entregador (delivery/retirada). |
| DELETE | `/{pedido_id}/entregador` | `remover_entregador_v2` | `PedidoAdminService.remover_entregador` | Desvincula entregador atual. |

## Client – `app/api/pedidos/router/client/router_pedidos_client.py`

Prefixo base: `/api/pedidos/client` (autenticação via `get_cliente_by_super_token`).

| Método | Caminho | Handler | Service principal | Notas |
| --- | --- | --- | --- | --- |
| POST | `/checkout/preview` | `preview_checkout` | `PedidoService` (`calcular_preview_checkout`) | Calcula totais sem persistir; usa cliente autenticado. |
| POST | `/checkout` | `finalizar_checkout` | `PedidoService` (`finalizar_pedido`) ou `PedidoMesaService`/`PedidoBalcaoService` | Fluxo depende de `tipo_pedido`; cria pedido delivery/mesa/balcão. |
| GET | `/` | `listar_pedidos` | `PedidoService` (`listar_pedidos_cliente_unificado`) | Lista pedidos do cliente com paginação (`skip/limit`). |
| PUT | `/{pedido_id}/itens` | `atualizar_item_cliente` | `PedidoService` (`atualizar_item_pedido`) | Atualiza itens do pedido; valida que pertence ao cliente. |
| PUT | `/{pedido_id}/editar` | `atualizar_pedido_cliente` | `PedidoService` (`editar_pedido_parcial`) | Marcado como legada/compatível; recomenda uso do gateway orquestrador. |
| PUT | `/{pedido_id}/modo-edicao` | `alterar_modo_edicao` | — | Endpoint bloqueado (retorna 403); documentação indica desativado para clientes. |

---

### Próximos passos sugeridos

1. Mapear consumidores front (`@/actions/pedidos/*`) e integrações externas para cada rota.
2. Consolidar riscos/regressões identificados durante a inspeção.

