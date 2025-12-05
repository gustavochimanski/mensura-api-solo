## Plano de Unificação das Rotas de Pedidos

### 1. Objetivo
- Consolidar operações de pedidos (mesa, delivery, balcão) em rotas REST genéricas, reduzindo duplicidade e divergência de comportamento.
- Padronizar contratos (payload, status HTTP, respostas) e facilitar a evolução para novos canais sem impacto exponencial no front.

### 2. Escopo
- Rotas admin de pedidos (`app/api/pedidos/router/admin/router_pedidos_admin.py`) e services associados.
- Documentação pública (`docs/API_PEDIDOS_UNIFICADOS_ADMIN.md`) e integrações do front (`@/actions/pedidos/*`).
- Manutenção temporária de rotas legadas via camada de compatibilidade.

### 3. Roadmap Proposto

#### Semana 1 — Mapeamento e diagnóstico
- Catalogar endpoints existentes por canal, incluindo payloads, respostas, regras especiais e dependências de service.
- Levantar pontos de consumo no front, integrações externas e automações que dependem das rotas legadas.
- Registrar riscos/regressões potenciais em uma planilha ou board compartilhado.

#### Semana 2 — Desenho do novo contrato
- Definir rotas unificadas por ação (`/itens`, `/observacoes`, `/status`, `/fechar-conta`, etc.) usando `tipo` ou inferência automática.
- Normalizar payloads e respostas (sempre `200` + pedido atualizado para mutações, enums padronizados, erros claros).
- Atualizar documentação em `docs/API_PEDIDOS_UNIFICADOS_ADMIN.md` e abrir para revisão de backend, frontend e QA.

#### Semana 3 — Camada de compatibilidade e arquitetura
- Projetar handlers de adaptação que encapsulem rotas antigas e redirecionem para os novos services.
- Definir estratégia de versionamento/rollout (ex.: header `x-api-version` ou query `v=2`) e logging de depreciação.
- Verificar impactos em autenticação/autorização e ajustar middlewares conforme necessário.

#### Semanas 4–5 — Implementação backend (fase 1)
- Refatorar services para centralizar a lógica por ação, parametrizando comportamentos por canal sem duplicação.
- Implementar rotas unificadas no router admin e manter rotas antigas operando via camada de compatibilidade.
- Criar testes unitários e de integração cobrindo cenários críticos (criação, itens, observações, status, fechamento de conta, entregador).

#### Semana 6 — Migração frontend (fase 1)
- Atualizar actions para consumir as novas rotas unificadas, controladas por feature flag/fallback.
- Garantir que fluxos críticos utilizem as rotas novas e, em caso de falha, revertam temporariamente às legadas.
- Alinhar cenários de QA regressivo com as novas chamadas.

#### Semanas 7–8 — Homologação e rollout controlado
- Disponibilizar em staging e executar testes exploratórios com QA, suporte e stakeholders de produto.
- Acompanhar métricas de erro, latência e uso das rotas antigas (via logs deprecation).
- Liberar gradualmente para subset de empresas/pontos de venda, ajustando conforme feedback.

#### Semana 9+ — Limpeza e estabilização
- Comunicar cronograma de desligamento das rotas legadas quando adoção das novas rotas for majoritária.
- Remover camada de compatibilidade e endpoints antigos; atualizar SDKs internos e documentação final.
- Conduzir retrospectiva registrando aprendizados e oportunidades de melhoria.

### 4. Entregáveis Principais
- Documentação atualizada (rotas unificadas, guia de migração, tabela de equivalência).
- Suite de testes automatizados cobrindo os novos endpoints.
- Logs e métricas para monitorar uso de rotas antigas e novas.
- Plano de comunicação interna (produto, suporte, QA) e externa (clientes parceiros, se aplicável).

### 5. Riscos e Mitigações
- **Regressão em fluxos críticos**: garantir fallback temporário e testes automatizados abrangentes.
- **Diferenças ocultas entre canais**: validar regras específicas durante o diagnóstico e ajustar parametrizações.
- **Adoção lenta do front**: aplicar rollout com feature flags e fornecer documentação clara para o time de frontend.
- **Integrações de terceiros**: identificar e apoiar parceiros durante o período de compatibilidade.

### 6. Próximos Passos Imediatos
- Agendar workshop rápido com backend/front/QA para validar o plano.
- Iniciar o mapeamento detalhado das rotas e consolidar os dados em um repositório compartilhado.
- Definir responsáveis por cada etapa do roadmap e alinhar expectativas de cronograma.

