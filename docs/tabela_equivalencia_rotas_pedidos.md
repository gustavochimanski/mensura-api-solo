# Tabela de Equivalência – Rotas Legadas vs Rotas `/api/pedidos/admin`

| Canal/Fluxo | Rota legada | Método | Rota unificada (`/api/pedidos/admin`) | Observações |
| --- | --- | --- | --- | --- |
| Geral | `/api/pedidos/admin/{pedido_id}` | GET | `/{pedido_id}` | Payload idêntico (`PedidoResponseCompletoTotal`). |
| Geral | `/api/pedidos/admin/{pedido_id}/historico` | GET | `/{pedido_id}/historico` | Mantém `HistoricoDoPedidoResponse`. |
| Geral | `/api/pedidos/admin/{pedido_id}/status?novo_status=` | PUT | `/{pedido_id}/status` | Query → body (`PedidoStatusPatchRequest`). |
| Geral | `/api/pedidos/admin/{pedido_id}` | DELETE | `/{pedido_id}` | Cancela pedido com `PedidoStatusEnum.C`. |
| Kanban | `/api/pedidos/admin/kanban` | GET | `/kanban` | Mesma resposta agrupada. |
| Delivery | `/api/pedidos/admin/delivery` | GET | `/?tipo=DELIVERY` | Filtros unificados (`empresa_id`, `cliente_id`, `status`, datas`). |
| Delivery | `/api/pedidos/admin/delivery` | POST | `/` | `PedidoCreateRequest.tipo_pedido=DELIVERY`. |
| Delivery | `/api/pedidos/admin/delivery/{id}` | PUT | `/{id}` | `PedidoUpdateRequest`. |
| Delivery | `/api/pedidos/admin/delivery/{id}/itens` | PUT | `/{id}/itens` | `PedidoItemMutationRequest` (`acao=ADD/UPDATE/REMOVE`). |
| Delivery | `/api/pedidos/admin/delivery/{id}/entregador` | PUT/DELETE | `/{id}/entregador` | `PedidoEntregadorRequest`. |
| Mesa | `/api/pedidos/admin/mesa` | GET | `/?tipo=MESA` | Retorno `PedidoResponseCompleto`. |
| Mesa | `/api/pedidos/admin/mesa` | POST | `/` | `PedidoCreateRequest.tipo_pedido=MESA`. |
| Mesa | `/api/pedidos/admin/mesa/{id}/adicionar-item` | PUT | `/{id}/itens` | `acao=ADD` com `produto_cod_barras`. |
| Mesa | `/api/pedidos/admin/mesa/{id}/adicionar-produto-generico` | PUT | `/{id}/itens` | `acao=ADD` com `receita_id`/`combo_id`. |
| Mesa | `/api/pedidos/admin/mesa/{id}/observacoes` | PUT | `/{id}/observacoes` | `PedidoObservacaoPatchRequest`. |
| Mesa | `/api/pedidos/admin/mesa/{id}/status` | PUT | `/{id}/status` | `PedidoStatusPatchRequest`. |
| Mesa | `/api/pedidos/admin/mesa/{id}/fechar-conta` | PUT | `/{id}/fechar-conta` | `PedidoFecharContaRequest`. |
| Mesa | `/api/pedidos/admin/mesa/{id}/reabrir` | PUT | `/{id}/reabrir` | Mesma lógica. |
| Mesa | `/api/pedidos/admin/mesa/{id}/item/{item_id}` | DELETE | `/{id}/itens/{item_id}` | `acao=REMOVE`. |
| Mesa | `/api/pedidos/admin/mesa/{mesa_id}/finalizados` | GET | `/?tipo=MESA&status=E&mesa_id=` | Usar filtros combinados. |
| Mesa | `/api/pedidos/admin/mesa/cliente/{cliente_id}` | GET | `/?tipo=MESA&cliente_id=` | Ajustar filtros. |
| Entregador | `/api/pedidos/admin/{id}/entregador` | PUT/DELETE | `/{id}/entregador` | Único endpoint para vincular/desvincular. |
| Balcão* | `/api/pedidos/admin/balcao*` | vários | `/` | Ações equivalentes via `tipo_pedido=BALCAO`. |

\*Rotas de balcão no legado estão concentradas em `service_pedidos_balcao`. Substitua por chamadas unificadas usando `tipo_pedido=BALCAO`.

## Como usar

1. Atualize a documentação pública com esta tabela (linkando no guia de migração).
2. Para cada chamada legada, valide se o front ou integração já suporta os filtros/DTOs do contrato unificado.
3. Use os logs de depreciação (`Deprecation`, `Link`) para monitorar adoção e planejar o desligamento definitivo.

