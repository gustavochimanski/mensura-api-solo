# Mapeamento de Rotas de Pedidos (Semana 1)

Este documento consolida as rotas atuais de pedidos por canal, com foco no diagnóstico inicial do plano de unificação.

## Admin – `app/api/pedidos/router/admin/router_pedidos_admin.py`

Prefixo base: `/api/pedidos/admin` (todas as rotas exigem `Depends(get_current_user)`).

### Endpoints Unificados

| Método | Caminho | Handler | Service principal | Notas |
| --- | --- | --- | --- | --- |
| GET | `/` | `listar_pedidos` | `PedidoAdminService.listar_pedidos` | Filtros `empresa_id`, `tipo`, `status`, `cliente_id`, `mesa_id`, datas, paginação. |
| GET | `/kanban` | `listar_kanban` | `PedidoAdminService.listar_kanban` | Mantém retorno `KanbanAgrupadoResponse`. |
| GET | `/{pedido_id}` | `obter_pedido` | `PedidoAdminService.obter_pedido` | Responde `PedidoResponseCompletoTotal`. |
| GET | `/{pedido_id}/historico` | `obter_historico` | `PedidoAdminService.obter_historico` | Histórico unificado. |
| POST | `/` | `criar_pedido` | `PedidoAdminService.criar_pedido` | Usa `PedidoCreateRequest` com `tipo_pedido` (`DELIVERY`, `MESA`, `BALCAO`). |
| PUT | `/{pedido_id}` | `atualizar_pedido` | `PedidoAdminService.atualizar_pedido` | Atualiza metadados comuns (`PedidoUpdateRequest`). |
| PATCH | `/{pedido_id}/status` | `atualizar_status` | `PedidoAdminService.atualizar_status` | Status via `PedidoStatusPatchRequest`. |
| PATCH | `/{pedido_id}/observacoes` | `atualizar_observacoes` | `PedidoAdminService.atualizar_observacoes` | Observações gerais (delivery) ou específicas (mesa/balcão). |
| PATCH | `/{pedido_id}/fechar-conta` | `fechar_conta` | `PedidoAdminService.fechar_conta` | Usa `PedidoFecharContaRequest` (apenas mesa/balcão). |
| PATCH | `/{pedido_id}/reabrir` | `reabrir_pedido` | `PedidoAdminService.reabrir` | Reabre pedido conforme regras do tipo. |
| DELETE | `/{pedido_id}` | `cancelar_pedido` | `PedidoAdminService.cancelar` | Define status `CANCELADO`. |
| POST | `/{pedido_id}/itens` | `gerenciar_itens` | `PedidoAdminService.gerenciar_item` | `PedidoItemMutationRequest` com ação `ADD/UPDATE/REMOVE`. |
| PATCH | `/{pedido_id}/itens/{item_id}` | `atualizar_item` | `PedidoAdminService.gerenciar_item` | Força ação `UPDATE`. |
| DELETE | `/{pedido_id}/itens/{item_id}` | `remover_item` | `PedidoAdminService.remover_item` | Remove item específico. |
| PUT | `/{pedido_id}/entregador` | `atualizar_entregador` | `PedidoAdminService.atualizar_entregador` | Vincula/desvincula entregador (delivery/retirada). |
| DELETE | `/{pedido_id}/entregador` | `remover_entregador` | `PedidoAdminService.remover_entregador` | Remove entregador atual. |

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

