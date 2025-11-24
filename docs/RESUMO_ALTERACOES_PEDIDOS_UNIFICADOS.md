# Resumo Técnico - Unificação de Pedidos

## 🎯 Objetivo

Unificar todos os pedidos (DELIVERY, MESA, BALCAO) em um único repositório, serviço e router, conforme solicitado.

---

## 📦 O que foi Alterado

### 1. Repositório Unificado

**Arquivo**: `app/api/pedidos/repositories/repo_pedidos.py`

#### Métodos Adicionados

**Criação de Pedidos:**
- `criar_pedido_delivery()` - Cria pedido de delivery
- `criar_pedido_balcao()` - Cria pedido de balcão
- `criar_pedido_mesa()` - Cria pedido de mesa
- `criar_pedido()` - Alias para `criar_pedido_delivery()` (compatibilidade)

**Métodos Unificados:**
- `get(pedido_id, tipo_pedido)` - Busca pedido por ID e tipo
- `get_pedido(pedido_id, tipo_pedido=None)` - Busca pedido (com filtro opcional por tipo)
- `add_item()` - Adiciona item ao pedido (produto, receita ou combo)
- `remove_item()` - Remove item do pedido
- `cancelar()` - Cancela pedido
- `confirmar()` - Confirma pedido (status → IMPRESSAO)
- `fechar_conta()` - Fecha conta (status → ENTREGUE)
- `reabrir()` - Reabre pedido cancelado/entregue
- `atualizar_status()` - Atualiza status do pedido

**Métodos de Listagem:**
- `list_abertos_by_mesa(mesa_id, tipo_pedido, empresa_id)` - Lista pedidos abertos de uma mesa
- `list_abertos_all(tipo_pedido, empresa_id)` - Lista todos os pedidos abertos
- `get_aberto_mais_recente(mesa_id, tipo_pedido, empresa_id)` - Busca pedido aberto mais recente
- `list_finalizados(tipo_pedido, data_filtro, empresa_id, mesa_id)` - Lista pedidos finalizados
- `list_by_cliente_id(cliente_id, tipo_pedido, empresa_id, skip, limit)` - Lista pedidos de um cliente

**Métodos de Itens:**
- `adicionar_item_produto()` - Adiciona item de produto
- `adicionar_item_receita()` - Adiciona item de receita
- `adicionar_item_combo()` - Adiciona item de combo

**Histórico:**
- `add_historico()` - Adiciona registro ao histórico
- `get_historico()` - Busca histórico do pedido

**Helpers:**
- `_calc_item_total()` - Calcula total de um item (incluindo adicionais)
- `_calc_total()` - Calcula total do pedido
- `_refresh_total()` - Recalcula e atualiza valor_total do pedido

#### Construtor Atualizado
```python
def __init__(self, db: Session, produto_contract: IProdutoContract | None = None):
    self.db = db
    self.produto_contract = produto_contract
```

---

### 2. Serviços Atualizados

**Arquivos**: 
- `app/api/pedidos/services/service_pedidos_balcao.py`
- `app/api/pedidos/services/service_pedidos_mesa.py`

#### Mudanças Principais

**Antes:**
```python
from app.api.pedidos.repositories.repo_pedidos_balcao import PedidoBalcaoRepository
from app.api.pedidos.repositories.repo_pedidos_mesa import PedidoMesaRepository

self.repo = PedidoBalcaoRepository(db, produto_contract=produto_contract)
```

**Depois:**
```python
from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
from app.api.pedidos.models.model_pedido_unificado import TipoPedido

self.repo = PedidoRepository(db, produto_contract=produto_contract)
```

**Métodos Atualizados:**
- Todos os métodos que chamavam `self.repo.get()` agora passam `TipoPedido.BALCAO` ou `TipoPedido.MESA`
- Métodos de criação agora usam `criar_pedido_balcao()` ou `criar_pedido_mesa()`
- Métodos de listagem agora passam `tipo_pedido` como parâmetro

---

### 3. Arquivos Removidos

- ❌ `app/api/pedidos/repositories/repo_pedidos_balcao.py`
- ❌ `app/api/pedidos/repositories/repo_pedidos_mesa.py`

---

### 4. Arquivos Atualizados

**Imports:**
- `app/api/pedidos/repositories/__init__.py` - Removidos exports dos repositórios separados
- `app/api/pedidos/services/__init__.py` - Mantidos exports dos serviços (compatibilidade)
- `app/api/cardapio/repositories/repo_printer.py` - Atualizado para usar repositório unificado

---

## 🔄 Como Usar o Repositório Unificado

### Exemplo: Criar Pedido de Balcão

```python
from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
from app.api.pedidos.models.model_pedido_unificado import TipoPedido

repo = PedidoRepository(db, produto_contract=produto_contract)

# Criar pedido
pedido = repo.criar_pedido_balcao(
    empresa_id=1,
    mesa_id=10,
    cliente_id=5,
    observacoes="Sem cebola"
)

# Adicionar item
pedido = repo.add_item(
    pedido_id=pedido.id,
    produto_cod_barras="7891234567890",
    quantidade=2,
    observacao="Sem cebola",
    adicionais_snapshot=[...]
)

# Buscar pedido
pedido = repo.get(pedido.id, TipoPedido.BALCAO)

# Listar pedidos abertos
pedidos = repo.list_abertos_all(TipoPedido.BALCAO, empresa_id=1)
```

### Exemplo: Criar Pedido de Mesa

```python
pedido = repo.criar_pedido_mesa(
    mesa_id=12,
    empresa_id=1,
    cliente_id=5,
    observacoes="Aniversário",
    num_pessoas=4
)

# Adicionar receita
repo.adicionar_item_receita(
    pedido_id=pedido.id,
    receita_id=8,
    quantidade=1,
    preco_unitario=12.00,
    observacao=None,
    adicionais_snapshot=[...]
)
```

### Exemplo: Criar Pedido de Delivery

```python
pedido = repo.criar_pedido_delivery(
    cliente_id=5,
    empresa_id=1,
    endereco_id=10,
    meio_pagamento_id=1,
    status="I",
    tipo_entrega="DELIVERY",
    origem="APP",
    endereco_snapshot={...},
    endereco_geo=...
)
```

---

## 📊 Estrutura de Dados

### PedidoUnificadoModel

Todos os pedidos usam o mesmo modelo com campo `tipo_pedido`:

```python
class PedidoUnificadoModel:
    id: int
    tipo_pedido: TipoPedido  # DELIVERY, MESA, BALCAO
    numero_pedido: str
    status: StatusPedido
    empresa_id: int
    cliente_id: int | None
    mesa_id: int | None  # Para MESA e BALCAO
    endereco_id: int | None  # Para DELIVERY
    # ... outros campos
```

### PedidoItemUnificadoModel

Itens podem ser produto, receita ou combo:

```python
class PedidoItemUnificadoModel:
    id: int
    pedido_id: int
    produto_cod_barras: str | None  # Se for produto
    receita_id: int | None  # Se for receita
    combo_id: int | None  # Se for combo
    quantidade: int
    preco_unitario: Decimal
    preco_total: Decimal
    # ... outros campos
```

**Validação**: Apenas um dos campos (`produto_cod_barras`, `receita_id`, `combo_id`) deve estar preenchido.

---

## 🔍 Diferenças por Tipo de Pedido

### DELIVERY
- Requer: `endereco_id`, `tipo_entrega`, `origem`
- Número: `DV-{sequencial}` (ex: `DV-000123`)
- Campos específicos: `endereco_snapshot`, `endereco_geo`, `distancia_km`, `previsao_entrega`, `entregador_id`

### MESA
- Requer: `mesa_id`, `empresa_id`
- Número: `{mesa.numero}-{sequencial}` (ex: `M12-001`)
- Campos específicos: `num_pessoas`

### BALCAO
- Requer: `empresa_id`, `cliente_id`
- Opcional: `mesa_id`
- Número: `BAL-{sequencial}` (ex: `BAL-000456`)

---

## ⚠️ Breaking Changes

### Para Desenvolvedores

1. **Imports**: Se você importava `PedidoBalcaoRepository` ou `PedidoMesaRepository`, agora deve usar `PedidoRepository`
2. **Métodos**: Métodos que não recebiam `tipo_pedido` agora precisam receber
3. **Queries**: Queries que filtravam por tipo agora devem usar `tipo_pedido` explicitamente

### Exemplo de Migração

**Antes:**
```python
from app.api.pedidos.repositories.repo_pedidos_balcao import PedidoBalcaoRepository

repo = PedidoBalcaoRepository(db)
pedido = repo.get(pedido_id)
```

**Depois:**
```python
from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
from app.api.pedidos.models.model_pedido_unificado import TipoPedido

repo = PedidoRepository(db, produto_contract=produto_contract)
pedido = repo.get(pedido_id, TipoPedido.BALCAO)
```

---

## ✅ Benefícios

1. **Código Unificado**: Um único repositório para todos os tipos de pedido
2. **Manutenção Simplificada**: Menos arquivos para manter
3. **Consistência**: Mesma lógica para todos os tipos de pedido
4. **Flexibilidade**: Fácil adicionar novos tipos de pedido no futuro
5. **Performance**: Menos queries duplicadas

---

## 🔗 Referências

- [API Admin](./API_PEDIDOS_UNIFICADOS_ADMIN.md)
- [API Client](./API_PEDIDOS_UNIFICADOS_CLIENT.md)
- [Plano de Migração](../PLANO_MIGRACAO_PEDIDOS_CENTRALIZADOS.md)

