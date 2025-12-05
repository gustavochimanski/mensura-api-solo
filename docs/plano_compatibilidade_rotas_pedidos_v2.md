# Plano de Compatibilidade e Rollout das Rotas de Pedidos Unificadas

## 1. Objetivo

Garantir a convivência controlada entre as rotas legadas de pedidos e a nova API unificada (`/api/pedidos/admin/v2`), permitindo migração gradual do frontend e de integrações externas sem regressões.

## 2. Estratégia Geral

1. **Router v2 isolado:** adicionar `router_pedidos_admin_v2.py` com prefixo `/api/pedidos/admin/v2`.
2. **Camada de serviço unificada:** todas as rotas (legadas e v2) delegam para `PedidoAdminService`, responsável por orquestrar regras compartilhadas + especializações.
3. **Feature flag:** habilitar uso das rotas v2 via flag (`PEDIDOS_V2_ENABLED`) consultada em middleware ou dependency.
4. **Versionamento por cabeçalho:** frontend envia `x-api-version: 2` para explicitar uso da versão nova; facilita métricas e roteamento.
5. **Logs de depreciação:** rotas legadas emitem log `warning` informando chamada, empresa e recomendação de migração.

## 3. Fluxo de Compatibilidade

### 3.1 Chamadas Legadas → Services Unificados

- Manter assinaturas atuais em `router_pedidos_admin.py`.
- Internamente, substituir chamadas diretas aos services antigos por métodos do `PedidoAdminService` (que irão reutilizar os services `PedidoService`, `PedidoMesaService`, etc.).
- Exemplos:
  - `GET /delivery` → `PedidoAdminService.listar_pedidos(tipo=DELIVERY)`.
  - `PUT /mesa/{pedido_id}/status` → `PedidoAdminService.atualizar_status(pedido_id, payload)`.

### 3.2 Redirecionamento Opcional

- Implementar helper `ensure_v2_enabled(request)` que, quando a flag estiver ativa e o cabeçalho `x-api-version: 2` estiver ausente, adiciona header de alerta (`Deprecation`) e sugestão de migração.
- Para ambientes internos, podemos responder `308 Permanent Redirect` apontando para o endpoint v2 equivalente (configurável).

## 4. Monitoramento e Métricas

- **Logs estruturados:** incluir campos `rota_origem`, `rota_destino`, `empresa_id`, `tipo_pedido`.
- **Dashboard:** acompanhar taxa de requisições v2 vs legado, erros por rota e tempos de resposta.
- **Alertas:** configurar alertas quando chamadas legadas excederem o limite planejado após data-alvo de desalocação.

## 5. Rollout Proposto

1. **Fase 0 (dev/staging):** habilitar flag v2 apenas para QA/backend.
2. **Fase 1 (beta controlado):** liberar para um conjunto pequeno de empresas com suporte próximo.
3. **Fase 2 (default on):** ativar flag por padrão; rotas legadas ainda disponíveis, mas com log depreciação.
4. **Fase 3 (sunset):** bloquear criação de novos pedidos via rotas legadas, mantendo apenas leitura. Comunicar data de desligamento.
5. **Fase 4 (remoção):** retirar rotas legadas e a camada de compatibilidade.

## 6. Tarefas Técnicas

- [x] Criar `PedidoAdminService` centralizando operações.
- [x] Implementar router v2 com endpoints definidos em `docs/API_PEDIDOS_UNIFICADOS_ADMIN.md`.
- [ ] Ajustar rotas legadas para usar `PedidoAdminService`.
- [x] Adicionar middleware/utility para logs e verificação de flag (`PEDIDOS_V2_ENABLED`).
- [ ] Configurar métricas e alertas (observability).
- [ ] Atualizar testes existentes e criar novos cenários para o fluxo v2.
- [ ] Documentar guia de migração para frontend e integrações.

## 7. Riscos e Mitigações

| Risco | Mitigação |
| --- | --- |
| Divergência de comportamento entre v1 e v2 | Testes de contrato automatizados comparando respostas para casos críticos. |
| Adoção lenta do frontend | Feature flag individual por empresa para habilitar progressivamente. |
| Serviços legados não preparados para novos DTOs | Implementar adaptadores no `PedidoAdminService` para converter estruturas antigas. |
| Logs/métricas insuficientes | Instrumentar desde o primeiro deploy em staging. |

## 8. Comunicação

- Comunicar datas e fases no canal interno (produto/suporte/QA).
- Disponibilizar tabela de equivalência (arquivo separado linkado na documentação principal).
- Atualizar FAQ e runbook de suporte com instruções sobre a flag e troubleshooting.

