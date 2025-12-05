# Plano de Compatibilidade e Rollout das Rotas de Pedidos Unificadas

## 1. Objetivo

Garantir a convivência controlada entre as rotas legadas de pedidos e a nova API unificada (`/api/pedidos/admin/v2`), permitindo migração gradual do frontend e de integrações externas sem regressões.

## 2. Estratégia Geral

1. **Router unificado:** `router_pedidos_admin.py` expõe `/api/pedidos/admin` com o contrato padronizado.
2. **Camada de serviço unificada:** todas as rotas delegam para `PedidoAdminService`, responsável por orquestrar regras compartilhadas + especializações.
3. **Controle gradual:** habilitar a disseminação do novo contrato via feature flag por empresa/ambiente (no API Gateway ou serviço de configuração).
4. **Observabilidade ativa:** registrar logs estruturados, métricas e alertas específicos para monitorar adoção e regressões.
5. **Comunicação contínua:** informar clientes internos/externos sobre cronograma e implicações da remoção das rotas legadas.

## 3. Fluxo de Compatibilidade

### 3.1 Chamadas Legadas → Services Unificados

- Manter assinaturas atuais em `router_pedidos_admin.py`.
- Internamente, substituir chamadas diretas aos services antigos por métodos do `PedidoAdminService` (que irão reutilizar os services `PedidoService`, `PedidoMesaService`, etc.).
- Exemplos:
  - `GET /delivery` → `PedidoAdminService.listar_pedidos(tipo=DELIVERY)`.
  - `PUT /mesa/{pedido_id}/status` → `PedidoAdminService.atualizar_status(pedido_id, payload)`.

### 3.2 Comunicação e depreciação

- Expor headers de `Deprecation`/`Link` via API Gateway ou middleware para sinalizar clientes que ainda consomem contratos antigos.
- Registrar logs estruturados (`rota_origem`, `empresa_id`, `user_agent`) para acompanhar o progresso de migração.
- Opcional: implementar redirecionamento (308) em camadas superiores quando o contrato antigo for usado.

## 4. Monitoramento e Métricas

- **Logs estruturados:** incluir campos `rota_origem`, `rota_destino`, `empresa_id`, `tipo_pedido`.
- **Dashboard:** acompanhar taxa de requisições v2 vs legado, erros por rota e tempos de resposta.
- **Alertas:** configurar alertas quando chamadas legadas excederem o limite planejado após data-alvo de desalocação.

## 5. Rollout Proposto

| Fase | Ambiente/escopo | Ações principais | Critérios de avanço |
| --- | --- | --- | --- |
| 0 – Dev/Staging | Squad backend + QA | Habilitar `PEDIDOS_V2_ENABLED=True` apenas nestes ambientes. Validar rotas v2 com suite automatizada e smoke manual. | Testes de regressão verdes, documentação revisada. |
| 1 – Pilot | 3-5 empresas piloto | Ativar flag por empresa (feature flag/tenant). Monitorar logs de depreciação, erros 5xx, tempo de resposta. | Nenhum incidente crítico por 1 semana; feedback positivo dos pilotos. |
| 2 – Default ON | Todas as empresas | Habilitar v2 por padrão, manter rotas legadas acessíveis com headers de depreciação. Disponibilizar canal de suporte. | Uso das rotas legadas < 20% das requisições totais por 2 semanas. |
| 3 – Sunset | Todas as empresas | Bloquear mutações nas rotas legadas (responder 410 ou redirecionar). Somente leitura permitida para consultas históricas. | Nenhuma requisição crítica nas rotas bloqueadas por 1 semana. |
| 4 – Remoção | Todas as empresas | Remover camada de compatibilidade, código e documentação legado. Atualizar SDKs internos e avisar parceiros. | Aprovação de produto/CS; métricas alinhadas. |

## 6. Tarefas Técnicas

- [x] Criar `PedidoAdminService` centralizando operações.
- [x] Implementar router v2 com endpoints definidos em `docs/API_PEDIDOS_UNIFICADOS_ADMIN.md`.
- [x] Ajustar rotas legadas para usar `PedidoAdminService`.
- [x] Adicionar middleware/utility para logs e verificação de flag (`PEDIDOS_V2_ENABLED`).
- [ ] Configurar métricas e alertas (observability).
- [ ] Atualizar testes existentes e criar novos cenários para o fluxo v2.
- [x] Documentar guia de migração para frontend e integrações.

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

