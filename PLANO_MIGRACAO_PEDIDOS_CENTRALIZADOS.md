# Plano de Migração - Centralização de Pedidos no Schema Pedidos

## Objetivo
Centralizar todas as tabelas de pedidos (balcão, mesa, delivery) em uma única estrutura unificada no schema `pedidos`, com uma tabela de itens que suporta produto, combo e receita através de colunas nullable.

## Situação Atual

### Tabelas de Pedidos (a serem removidas):
1. **balcao.pedidos_balcao** (PedidoBalcaoModel)
2. **balcao.pedido_balcao_itens** (PedidoBalcaoItemModel)
3. **mesas.pedidos_mesa** (PedidoMesaModel)
4. **mesas.pedido_mesa_itens** (PedidoMesaItemModel)
5. **cardapio.pedidos_dv** (PedidoDeliveryModel)
6. **cardapio.pedido_itens_dv** (PedidoItemModel)

### Tabelas de Histórico (a serem migradas):
1. **balcao.pedido_balcao_historico** (PedidoBalcaoHistoricoModel) - histórico detalhado com tipo_operacao
2. **cardapio.pedido_status_historico_dv** (PedidoStatusHistoricoModel) - histórico de status de delivery

### Tabelas Unificadas Existentes (no schema pedidos):
- **pedidos.pedidos** (PedidoModel) - já existe estrutura unificada
- **pedidos.pedidos_itens** (PedidoUnificadoItemModel) - já tem combo_id, mas falta receita_id

## Nova Estrutura Proposta

### 1. Tabela: `pedidos.pedidos` (PedidoUnificadoModel)

**Colunas principais:**
- `id` (PK)
- `tipo_pedido` (Enum: BALCAO, MESA, DELIVERY)
- `empresa_id` (FK)
- `numero_pedido` (String, único por empresa)
- `status` (Enum: P, I, R, S, E, C, D, X, A)
- `mesa_id` (FK, nullable - para BALCAO e MESA)
- `cliente_id` (FK, nullable)
- `endereco_id` (FK, nullable - para DELIVERY)
- `entregador_id` (FK, nullable - para DELIVERY)
- `meio_pagamento_id` (FK, nullable)
- `cupom_id` (FK, nullable)
- `tipo_entrega` (Enum: DELIVERY, RETIRADA - apenas DELIVERY)
- `origem` (Enum: WEB, APP, BALCAO - apenas DELIVERY)
- `subtotal`, `desconto`, `taxa_entrega`, `taxa_servico`, `valor_total`
- `observacoes`, `observacao_geral`
- `num_pessoas` (Integer, nullable - para MESA)
- `troco_para` (Numeric, nullable)
- `previsao_entrega` (DateTime, nullable - para DELIVERY)
- `distancia_km` (Numeric, nullable - para DELIVERY)
- `endereco_snapshot` (JSONB, nullable - para DELIVERY)
- `endereco_geo` (Geography, nullable - para DELIVERY)
- `produtos_snapshot` (JSONB, nullable - legado, pode ser removido)
- `acertado_entregador` (Boolean, default False)
- `acertado_entregador_em` (DateTime, nullable)
- `created_at`, `updated_at`

### 2. Tabela: `pedidos.pedidos_itens` (PedidoItemUnificadoModel)

**Colunas principais:**
- `id` (PK)
- `pedido_id` (FK -> pedidos.pedidos.id)
- `produto_cod_barras` (String, FK -> catalogo.produtos.cod_barras, **nullable**)
- `combo_id` (Integer, FK -> catalogo.combos.id, **nullable**)
- `receita_id` (Integer, FK -> catalogo.receitas.id, **nullable**)
- `quantidade` (Integer, default 1)
- `preco_unitario` (Numeric(18, 2))
- `preco_total` (Numeric(18, 2))
- `observacao` (String(500), nullable)
- `produto_descricao_snapshot` (String(255), nullable)
- `produto_imagem_snapshot` (String(255), nullable)
- `adicionais_snapshot` (JSON, nullable)

**Validação:** Apenas um dos campos (produto_cod_barras, combo_id, receita_id) deve ser preenchido.

### 3. Tabela: `pedidos.pedidos_historico` (PedidoHistoricoUnificadoModel)

**Colunas principais:**
- `id` (PK)
- `pedido_id` (FK -> pedidos.pedidos.id)
- `tipo_operacao` (Enum - opcional, para histórico detalhado como balcão)
- `status_anterior` (Enum, nullable)
- `status_novo` (Enum, nullable)
- `descricao` (Text, nullable)
- `motivo` (Text, nullable)
- `observacoes` (Text, nullable)
- `usuario_id` (FK, nullable)
- `cliente_id` (FK, nullable)
- `ip_origem` (String(45), nullable)
- `user_agent` (String(500), nullable)
- `created_at` (DateTime)

## Estrutura de Chaves Estrangeiras

### Produto
- **Tabela:** `catalogo.produtos`
- **Chave primária:** `cod_barras` (String)
- **Referência:** `produto_cod_barras` (String)

### Combo
- **Tabela:** `catalogo.combos`
- **Chave primária:** `id` (Integer)
- **Referência:** `combo_id` (Integer)

### Receita
- **Tabela:** `catalogo.receitas`
- **Chave primária:** `id` (Integer)
- **Referência:** `receita_id` (Integer)

## Etapas de Migração

### Fase 1: Criação dos Novos Modelos
1. ✅ Criar `app/api/pedidos/models/model_pedido_unificado.py`
   - Modelo `PedidoUnificadoModel` com todas as colunas necessárias
   - Enums: TipoPedido, StatusPedido, TipoEntrega, OrigemPedido
   - Relacionamentos com itens, histórico, transações
   - **Schema:** `pedidos` (não `cardapio`)

2. ✅ Criar `app/api/pedidos/models/model_pedido_item_unificado.py`
   - Modelo `PedidoItemUnificadoModel` com produto_cod_barras, combo_id, receita_id
   - Validação no modelo para garantir que apenas um campo está preenchido
   - Relacionamentos com pedido, produto, combo, receita
   - **Schema:** `pedidos` (não `cardapio`)

3. ✅ Criar `app/api/pedidos/models/model_pedido_historico_unificado.py`
   - Modelo `PedidoHistoricoUnificadoModel` para histórico unificado
   - Suporta histórico simples (status) e detalhado (tipo_operacao)
   - **Schema:** `pedidos` (não `cardapio`)

### Fase 2: Script de Migração de Dados
4. ⏭️ **PULADO** - Script de migração não será criado (banco será recriado)
   - ~~Migrar dados de `balcao.pedidos_balcao` → `pedidos.pedidos` (tipo_pedido='BALCAO')~~
   - ~~Migrar dados de `mesas.pedidos_mesa` → `pedidos.pedidos` (tipo_pedido='MESA')~~
   - ~~Migrar dados de `cardapio.pedidos_dv` → `pedidos.pedidos` (tipo_pedido='DELIVERY')~~
   - **Nota:** O banco será recriado, então não é necessário script de migração

### Fase 3: Atualização de Serviços e Repositórios
5. ✅ Atualizar repositórios e serviços de balcão
   - ✅ `app/api/pedidos/repositories/repo_pedidos_balcao.py` (movido de `balcao/repositories`)
   - ✅ `app/api/pedidos/services/service_pedidos_balcao.py` (movido de `balcao/services`)
   - Alterar referências de `PedidoBalcaoModel` → `PedidoUnificadoModel`
   - Alterar referências de `PedidoBalcaoItemModel` → `PedidoItemUnificadoModel`
   - Ajustar queries e filtros para `tipo_pedido == TipoPedido.BALCAO.value`
   - Atualizar imports em todos os arquivos que usam esses serviços

6. ✅ Atualizar repositórios e serviços de mesas
   - ✅ `app/api/pedidos/repositories/repo_pedidos_mesa.py` (movido de `mesas/repositories`)
   - ✅ `app/api/pedidos/services/service_pedidos_mesa.py` (movido de `mesas/services`)
   - Alterar referências de `PedidoMesaModel` → `PedidoUnificadoModel`
   - Alterar referências de `PedidoMesaItemModel` → `PedidoItemUnificadoModel`
   - Ajustar queries e filtros para `tipo_pedido == TipoPedido.MESA.value`
   - Atualizar imports em todos os arquivos que usam esses serviços

7. ✅ Atualizar repositório e serviços de cardapio/delivery
   - ✅ `app/api/pedidos/repositories/repo_pedidos.py` (movido de `cardapio/repositories`)
   - ✅ `app/api/cardapio/services/pedidos/service_pedido.py` (atualizado)
   - ✅ `app/api/cardapio/services/pedidos/service_pedido_responses.py` (atualizado)
   - ✅ `app/api/cardapio/services/pedidos/service_pedido_helpers.py` (atualizado)
   - Alterar referências de `PedidoDeliveryModel` → `PedidoUnificadoModel`
   - Alterar referências de `PedidoItemModel` → `PedidoItemUnificadoModel`
   - Ajustar queries e filtros para `tipo_pedido == TipoPedido.DELIVERY.value`
   - Atualizar imports em todos os arquivos que usam esses serviços

### Fase 4: Atualização de Schemas Pydantic
8. ✅ Atualizar schemas de balcão
   - ✅ `app/api/balcao/schemas/schema_pedido_balcao.py` - Já suporta receita_id e combo_id via `AdicionarProdutoGenericoRequest`
   - Ajustado para refletir nova estrutura

9. ✅ Atualizar schemas de mesas
   - ✅ `app/api/mesas/schemas/schema_pedido_mesa.py` - Já suporta receita_id e combo_id via `AdicionarProdutoGenericoRequest`
   - Ajustado para refletir nova estrutura

10. ✅ Atualizar schemas de cardapio/delivery
    - ✅ `app/api/cardapio/schemas/schema_pedido.py` - Atualizado `ItemPedidoResponse` para suportar `combo_id` e `receita_id` (nullable)
    - ⏳ `app/api/cardapio/schemas/schema_pedido_cliente.py` - Pendente revisão
    - ✅ `app/api/cardapio/schemas/schema_pedido_status_historico.py` - Atualizado para suportar modelo unificado (status_anterior, status_novo, tipo_operacao)
    - ✅ Ajustado para refletir nova estrutura de itens
    - **Nota:** Considerar mover para `app/api/pedidos/schemas/`

### Fase 5: Atualização de Routers
11. ✅ Atualizar routers de balcão
    - ✅ Atualizados imports para usar modelos unificados
    - ✅ Atualizados imports para usar serviços de `pedidos` domain
    - Verificar todos os endpoints que usam os modelos antigos
    - Atualizar imports e referências

12. ✅ Atualizar routers de mesas
    - ✅ Atualizados imports para usar modelos unificados
    - ✅ Atualizados imports para usar serviços de `pedidos` domain
    - Verificar todos os endpoints que usam os modelos antigos
    - Atualizar imports e referências

13. ✅ Atualizar routers de cardapio
    - ✅ Atualizado router admin para usar modelo unificado de histórico
    - ✅ Router client já usa serviços atualizados
    - ✅ Atualizados response builders para suportar combo_id e receita_id nos itens
    - ✅ Atualizado método `build_historico_response` para modelo unificado

### Fase 6: Criação das Tabelas (Banco será Recriado)
14. ⏭️ **PULADO** - Migration Alembic não será necessária
    - As tabelas serão criadas automaticamente quando o banco for recriado
    - `init_db.py` já está configurado para criar as tabelas unificadas no schema `pedidos`
    - Índices e constraints serão criados automaticamente pelos modelos SQLAlchemy
    - **Nota:** O banco será resetado, então não é necessário migration Alembic

### Fase 7: Limpeza
15. ⏳ Remover modelos antigos
    - `app/api/balcao/models/model_pedido_balcao.py`
    - `app/api/balcao/models/model_pedido_balcao_item.py`
    - `app/api/mesas/models/model_pedido_mesa.py`
    - `app/api/mesas/models/model_pedido_mesa_item.py`
    - `app/api/cardapio/models/model_pedido_dv.py`
    - `app/api/cardapio/models/model_pedido_item_dv.py`

16. ✅ Atualizar `__init__.py` dos módulos
    - ✅ `app/api/pedidos/models/__init__.py` - Exporta modelos unificados
    - ✅ `app/api/pedidos/repositories/__init__.py` - Exporta repositórios
    - ✅ `app/api/pedidos/services/__init__.py` - Exporta serviços
    - Remover exports dos modelos antigos (quando remover os modelos)

17. ✅ Criar modelo unificado de histórico
    - ✅ `app/api/pedidos/models/model_pedido_historico_unificado.py`
    - Suportar tanto histórico simples (status) quanto detalhado (tipo_operacao)
    - **Schema:** `pedidos` (não `cardapio`)

## Considerações Importantes

### Validação de Dados
- Implementar constraint CHECK na tabela de itens para garantir que apenas um dos campos (produto_cod_barras, combo_id, receita_id) está preenchido
- Validar no código Python também antes de inserir

### Compatibilidade
- Manter compatibilidade com código existente durante a migração
- Criar views ou aliases temporários se necessário

### Performance
- Criar índices apropriados:
  - `idx_pedidos_empresa_tipo_status` (empresa_id, tipo_pedido, status)
  - `idx_pedidos_itens_pedido` (pedido_id)
  - `idx_pedidos_itens_produto` (produto_cod_barras) WHERE produto_cod_barras IS NOT NULL
  - `idx_pedidos_itens_combo` (combo_id) WHERE combo_id IS NOT NULL
  - `idx_pedidos_itens_receita` (receita_id) WHERE receita_id IS NOT NULL

### Snapshots JSON
- Os snapshots JSON (`produtos_snapshot`) podem ser mantidos temporariamente para referência
- Após validação, podem ser removidos ou mantidos apenas para histórico

### Testes
- Criar testes unitários para os novos modelos
- Criar testes de integração para validar a migração
- Testar todos os endpoints após a migração

## Ordem de Execução Recomendada

1. **Desenvolvimento em paralelo:**
   - Criar novos modelos
   - Criar novos schemas
   - Atualizar serviços (em branch separada)

2. **Reset do banco:**
   - Resetar banco de dados (desenvolvimento/teste)
   - As tabelas serão criadas automaticamente via `init_db.py`
   - Validar criação das tabelas unificadas

3. **Deploy:**
   - Resetar banco de dados (as tabelas serão criadas automaticamente via `init_db.py`)
   - Deploy do código atualizado
   - Monitorar erros

4. **Limpeza:**
   - Após validação (1-2 semanas)
   - Remover modelos antigos
   - Remover snapshots JSON se não forem mais necessários

## Arquivos a Criar/Modificar

### Novos Arquivos (✅ Criados):
- ✅ `app/api/pedidos/models/model_pedido_unificado.py`
- ✅ `app/api/pedidos/models/model_pedido_item_unificado.py`
- ✅ `app/api/pedidos/models/model_pedido_historico_unificado.py`
- ⏭️ `scripts/migrate_pedidos_to_cardapio.py` (não necessário - banco será recriado)
- ⏭️ `alembic/versions/XXXX_migrate_pedidos_to_pedidos.py` (não necessário - banco será resetado)

### Arquivos a Modificar:
- ✅ Repositórios movidos para `app/api/pedidos/repositories/`:
  - ✅ `repo_pedidos_balcao.py` (movido de `balcao/repositories`)
  - ✅ `repo_pedidos_mesa.py` (movido de `mesas/repositories`)
  - ✅ `repo_pedidos.py` (movido de `cardapio/repositories`)
- ✅ Serviços movidos/atualizados:
  - ✅ `app/api/pedidos/services/service_pedidos_balcao.py` (movido)
  - ✅ `app/api/pedidos/services/service_pedidos_mesa.py` (movido)
  - ✅ `app/api/cardapio/services/pedidos/service_pedido.py` (atualizado)
  - ✅ `app/api/cardapio/services/pedidos/service_pedido_responses.py` (atualizado)
  - ✅ `app/api/cardapio/services/pedidos/service_pedido_helpers.py` (atualizado)
- ⏳ Todos os schemas relacionados (pendente)
- ✅ Routers atualizados (imports corrigidos):
  - ✅ Routers de balcão
  - ✅ Routers de mesas
  - ⏳ Routers de cardapio (parcial)
- ✅ `__init__.py` dos módulos de models atualizados

### Arquivos a Remover (✅ Concluído):
- ✅ `app/api/pedidos/models/model_pedido.py` (removido - duplicado, usar `model_pedido_unificado.py`)
- ✅ `app/api/pedidos/models/model_pedido_item.py` (removido - duplicado, usar `model_pedido_item_unificado.py`)
- ✅ `app/api/pedidos/models/model_pedido_historico.py` (removido - duplicado, usar `model_pedido_historico_unificado.py`)
- ✅ `app/api/cardapio/repositories/repo_pedidos.py` (removido - movido para `pedidos`)
- ⏳ `app/api/balcao/models/model_pedido_balcao.py` (será removido após reset do banco)
- ⏳ `app/api/balcao/models/model_pedido_balcao_item.py` (será removido após reset do banco)
- ⏳ `app/api/balcao/models/model_pedido_balcao_historico.py` (será removido após reset do banco)
- ⏳ `app/api/mesas/models/model_pedido_mesa.py` (será removido após reset do banco)
- ⏳ `app/api/mesas/models/model_pedido_mesa_item.py` (será removido após reset do banco)
- ✅ `app/api/cardapio/models/model_pedido_dv.py` (já foi removido - não existe mais)
- ✅ `app/api/cardapio/models/model_pedido_item_dv.py` (já foi removido - não existe mais)
- ✅ `app/api/cardapio/models/model_pedido_status_historico_dv.py` (já foi removido - não existe mais)

## Status Atual da Migração

### ✅ Concluído:
1. ✅ Modelos unificados criados no schema `pedidos`
2. ✅ Repositórios movidos para o domínio `pedidos`
3. ✅ Serviços de balcão e mesas movidos e atualizados
4. ✅ Serviços de delivery atualizados para usar modelos unificados
5. ✅ Imports atualizados em routers e adapters
6. ✅ Schema atualizado de `cardapio` para `pedidos` nos modelos
7. ✅ Schemas Pydantic atualizados para suportar combo_id e receita_id nos itens
8. ✅ Schema de histórico atualizado para modelo unificado
9. ✅ Routers de cardapio atualizados para usar modelo unificado de histórico
10. ✅ Response builders atualizados para suportar itens com produto/combo/receita
11. ✅ Repositório de relatórios atualizado com fallback para modelo unificado de histórico
12. ✅ **TODOS os schemas de pedidos movidos de `cardapio` para `pedidos`**
13. ✅ **TODOS os services de pedidos movidos de `cardapio` para `pedidos`**
14. ✅ **TODOS os routers de pedidos movidos de `cardapio` para `pedidos`**
15. ✅ **Todos os imports atualizados em todo o código**
16. ✅ **Router principal de cardapio atualizado para remover pedidos**
17. ✅ **Arquivos antigos removidos de `cardapio`**

### ⏳ Em Andamento:
1. Atualizar arquivos que ainda usam modelos antigos:
   - ✅ `app/api/pedidos/services/service_pedido.py` (atualizado para usar `PedidoUnificadoModel`)
   - ✅ `app/api/cadastros/services/service_endereco.py` (atualizado para usar `PedidoUnificadoModel`)
   - ✅ `app/api/relatorios/repositories/repository.py` (atualizado)
   - ✅ `app/database/init_db.py` (atualizado - inclui modelos unificados)
   - ✅ `app/main.py` (atualizado - imports modelos unificados)
   - ✅ `app/api/empresas/services/empresa_service.py` (atualizado)
   - ✅ `app/api/caixas/repositories/repo_caixa.py` (já usa `PedidoUnificadoModel`)
   - ✅ `app/api/financeiro/services/service_acerto_motoboy.py` (já usa `PedidoUnificadoModel`)
   - ✅ Models com relationships atualizados para usar `PedidoUnificadoModel`

### ⏳ Pendente:
1. ⏭️ **PULADO** - Migration Alembic não será necessária (banco será resetado)
2. Atualizar todos os arquivos restantes para usar modelos unificados:
   - ✅ `app/api/relatorios/repositories/repository.py` (atualizado)
   - ✅ `app/database/init_db.py` (atualizado)
   - ✅ `app/main.py` (atualizado)
   - ✅ `app/api/empresas/services/empresa_service.py` (atualizado)
   - ✅ `app/api/caixas/repositories/repo_caixa.py` (já usa `PedidoUnificadoModel`)
   - ✅ `app/api/financeiro/services/service_acerto_motoboy.py` (já usa `PedidoUnificadoModel`)
3. Resetar banco de dados (as tabelas serão criadas automaticamente)
4. Remover modelos antigos após reset do banco e validação
5. Testes e validação final

