# Tabela de Equivalência – Rotas Legadas vs Rotas `/api/pedidos/admin/v2`

| Canal/Fluxo | Rota legada | Método | Rota v2 equivalente | Observações |
| --- | --- | --- | --- | --- |
| Geral | `/api/pedidos/admin/{pedido_id}` | GET | `/api/pedidos/admin/v2/{pedido_id}` | Payload idêntico (`PedidoResponseCompletoTotal`). |
| Geral | `/api/pedidos/admin/{pedido_id}/historico` | GET | `/api/pedidos/admin/v2/{pedido_id}/historico` | Mantém `HistoricoDoPedidoResponse`. |
| Geral | `/api/pedidos/admin/{pedido_id}/status?novo_status=` | PUT | `/api/pedidos/admin/v2/{pedido_id}/status` | Query → body (`PedidoStatusPatchRequest`). |
| Geral | `/api/pedidos/admin/{pedido_id}` | DELETE | `/api/pedidos/admin/v2/{pedido_id}` | Cancela pedido com `PedidoStatusEnum.C`. |
| Kanban | `/api/pedidos/admin/kanban` | GET | `/api/pedidos/admin/v2/kanban` | Mesma resposta agrupada. |
| Delivery | `/api/pedidos/admin/delivery` | GET | `/api/pedidos/admin/v2?tipo=DELIVERY` | Filtros unificados (`empresa_id`, `cliente_id`, `status`, datas). |
| Delivery | `/api/pedidos/admin/delivery` | POST | `/api/pedidos/admin/v2` | `PedidoCreateRequest.tipo_pedido=DELIVERY`. |
| Delivery | `/api/pedidos/admin/delivery/{id}` | PUT | `/api/pedidos/admin/v2/{id}` | `PedidoUpdateRequest`. |
| Delivery | `/api/pedidos/admin/delivery/{id}/itens` | PUT | `/api/pedidos/admin/v2/{id}/itens` | `PedidoItemMutationRequest` (`acao=ADD/UPDATE/REMOVE`). |
| Delivery | `/api/pedidos/admin/delivery/{id}/entregador` | PUT/DELETE | `/api/pedidos/admin/v2/{id}/entregador` | `PedidoEntregadorRequest`. |
| Mesa | `/api/pedidos/admin/mesa` | GET | `/api/pedidos/admin/v2?tipo=MESA` | Retorno `PedidoResponseCompleto`. |
| Mesa | `/api/pedidos/admin/mesa` | POST | `/api/pedidos/admin/v2` | `PedidoCreateRequest.tipo_pedido=MESA`. |
| Mesa | `/api/pedidos/admin/mesa/{id}/adicionar-item` | PUT | `/api/pedidos/admin/v2/{id}/itens` | `acao=ADD` com `produto_cod_barras`. |
| Mesa | `/api/pedidos/admin/mesa/{id}/adicionar-produto-generico` | PUT | `/api/pedidos/admin/v2/{id}/itens` | `acao=ADD` com `receita_id`/`combo_id`. |
| Mesa | `/api/pedidos/admin/mesa/{id}/observacoes` | PUT | `/api/pedidos/admin/v2/{id}/observacoes` | `PedidoObservacaoPatchRequest`. |
| Mesa | `/api/pedidos/admin/mesa/{id}/status` | PUT | `/api/pedidos/admin/v2/{id}/status` | `PedidoStatusPatchRequest`. |
| Mesa | `/api/pedidos/admin/mesa/{id}/fechar-conta` | PUT | `/api/pedidos/admin/v2/{id}/fechar-conta` | `PedidoFecharContaRequest`. |
| Mesa | `/api/pedidos/admin/mesa/{id}/reabrir` | PUT | `/api/pedidos/admin/v2/{id}/reabrir` | Mesma lógica. |
| Mesa | `/api/pedidos/admin/mesa/{id}/item/{item_id}` | DELETE | `/api/pedidos/admin/v2/{id}/itens/{item_id}` | `acao=REMOVE`. |
| Mesa | `/api/pedidos/admin/mesa/{mesa_id}/finalizados` | GET | `/api/pedidos/admin/v2?tipo=MESA&status=E` | Filtrar por `status=E` e `mesa_id`. |
| Mesa | `/api/pedidos/admin/mesa/cliente/{cliente_id}` | GET | `/api/pedidos/admin/v2?tipo=MESA&cliente_id=` | Ajustar filtros. |
| Entregador | `/api/pedidos/admin/{id}/entregador` | PUT/DELETE | `/api/pedidos/admin/v2/{id}/entregador` | Único endpoint para vincular/desvincular. |
| Balcão* | `/api/pedidos/admin/balcao*` | vários | `/api/pedidos/admin/v2` | Ações equivalentes via `tipo_pedido=BALCAO`. Rotas legadas serão migradas na próxima etapa. |

\*Rotas de balcão no legado estão concentradas em `service_pedidos_balcao`. A etapa de unificação está em andamento; substitua por chamadas v2 usando `tipo_pedido=BALCAO`.

## Como usar

1. Atualize a documentação pública com esta tabela (linkando no guia de migração).
2. Para cada chamada legada, valide se o front ou integração já suporta os filtros/DTOS v2.
3. Use os logs de depreciação (`Deprecation`, `Link`) para monitorar adoção e planejar o desligamento definitivo.

