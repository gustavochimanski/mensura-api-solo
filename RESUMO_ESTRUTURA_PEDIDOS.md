# Resumo Visual - Estrutura de Pedidos

## Estrutura ANTES (Atual)

```
┌─────────────────────────────────────────────────────────────┐
│                    SCHEMA: balcao                           │
├─────────────────────────────────────────────────────────────┤
│  pedidos_balcao                                             │
│  ├─ id                                                      │
│  ├─ empresa_id                                              │
│  ├─ mesa_id                                                 │
│  ├─ cliente_id                                              │
│  ├─ numero_pedido                                           │
│  ├─ status                                                  │
│  └─ valor_total                                             │
│                                                              │
│  pedido_balcao_itens                                        │
│  ├─ id                                                      │
│  ├─ pedido_id → pedidos_balcao                             │
│  ├─ produto_cod_barras → produtos                            │
│  ├─ quantidade                                              │
│  └─ preco_unitario                                          │
│                                                              │
│  pedido_balcao_historico                                    │
│  └─ ...                                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    SCHEMA: mesas                            │
├─────────────────────────────────────────────────────────────┤
│  pedidos_mesa                                                │
│  ├─ id                                                      │
│  ├─ empresa_id                                              │
│  ├─ mesa_id                                                 │
│  ├─ cliente_id                                              │
│  ├─ numero_pedido                                           │
│  ├─ status                                                  │
│  └─ valor_total                                             │
│                                                              │
│  pedido_mesa_itens                                           │
│  ├─ id                                                      │
│  ├─ pedido_id → pedidos_mesa                               │
│  ├─ produto_cod_barras → produtos                           │
│  ├─ quantidade                                              │
│  └─ preco_unitario                                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    SCHEMA: cardapio                         │
├─────────────────────────────────────────────────────────────┤
│  pedidos_dv                                                  │
│  ├─ id                                                      │
│  ├─ empresa_id                                              │
│  ├─ cliente_id                                              │
│  ├─ endereco_id                                             │
│  ├─ entregador_id                                           │
│  ├─ status                                                  │
│  └─ valor_total                                             │
│                                                              │
│  pedido_itens_dv                                             │
│  ├─ id                                                      │
│  ├─ pedido_id → pedidos_dv                                 │
│  ├─ produto_cod_barras → produtos                           │
│  ├─ quantidade                                              │
│  └─ preco_unitario                                          │
│                                                              │
│  pedido_status_historico_dv                                  │
│  └─ ...                                                     │
└─────────────────────────────────────────────────────────────┘
```

**Problemas:**
- ❌ 3 tabelas de pedidos separadas
- ❌ 3 tabelas de itens separadas
- ❌ Receitas e combos armazenados em JSON (produtos_snapshot)
- ❌ Dificuldade para consultas unificadas
- ❌ Código duplicado entre módulos

---

## Estrutura DEPOIS (Proposta)

```
┌─────────────────────────────────────────────────────────────┐
│                    SCHEMA: cardapio                         │
├─────────────────────────────────────────────────────────────┤
│  pedidos (UNIFICADO)                                         │
│  ├─ id                                                      │
│  ├─ tipo_pedido (BALCAO | MESA | DELIVERY)                 │
│  ├─ empresa_id                                              │
│  ├─ numero_pedido                                           │
│  ├─ status                                                  │
│  ├─ mesa_id (nullable - para BALCAO e MESA)                 │
│  ├─ cliente_id (nullable)                                   │
│  ├─ endereco_id (nullable - para DELIVERY)                 │
│  ├─ entregador_id (nullable - para DELIVERY)               │
│  ├─ tipo_entrega (nullable - para DELIVERY)                │
│  ├─ origem (nullable - para DELIVERY)                       │
│  ├─ subtotal, desconto, taxa_entrega, taxa_servico         │
│  ├─ valor_total                                             │
│  ├─ observacoes, observacao_geral                          │
│  ├─ num_pessoas (nullable - para MESA)                      │
│  ├─ troco_para (nullable)                                  │
│  ├─ previsao_entrega (nullable - para DELIVERY)            │
│  ├─ distancia_km (nullable - para DELIVERY)                │
│  ├─ endereco_snapshot (JSONB, nullable)                     │
│  ├─ endereco_geo (Geography, nullable)                     │
│  └─ created_at, updated_at                                  │
│                                                              │
│  pedidos_itens (UNIFICADO)                                   │
│  ├─ id                                                      │
│  ├─ pedido_id → pedidos                                    │
│  ├─ produto_cod_barras → produtos (NULLABLE)               │
│  ├─ combo_id → combos (NULLABLE)                           │
│  ├─ receita_id → receitas (NULLABLE)                        │
│  ├─ quantidade                                              │
│  ├─ preco_unitario                                          │
│  ├─ preco_total                                             │
│  ├─ observacao                                              │
│  ├─ produto_descricao_snapshot                              │
│  ├─ produto_imagem_snapshot                                 │
│  └─ adicionais_snapshot (JSON)                              │
│                                                              │
│  pedidos_historico (UNIFICADO)                               │
│  ├─ id                                                      │
│  ├─ pedido_id → pedidos                                    │
│  ├─ tipo_operacao (nullable)                                │
│  ├─ status_anterior (nullable)                              │
│  ├─ status_novo (nullable)                                  │
│  ├─ descricao, motivo, observacoes                         │
│  ├─ usuario_id                                               │
│  ├─ cliente_id (nullable)                                   │
│  ├─ ip_origem, user_agent                                   │
│  └─ created_at                                              │
└─────────────────────────────────────────────────────────────┘
```

**Vantagens:**
- ✅ 1 única tabela de pedidos para todos os tipos
- ✅ 1 única tabela de itens com suporte a produto, combo e receita
- ✅ Relacionamentos diretos (FK) em vez de JSON
- ✅ Consultas unificadas mais simples
- ✅ Código centralizado e reutilizável
- ✅ Facilita relatórios e análises

---

## Mapeamento de Tipos de Item

### Antes (JSON snapshot):
```json
{
  "produtos": [...],
  "receitas": [
    {
      "receita_id": 5,
      "nome": "Pizza Margherita",
      "quantidade": 2,
      "preco_unitario": 25.00
    }
  ],
  "combos": [...]
}
```

### Depois (Tabela relacional):
```
pedidos_itens
├─ id: 1
├─ pedido_id: 100
├─ produto_cod_barras: NULL
├─ combo_id: NULL
├─ receita_id: 5          ← Relação direta!
├─ quantidade: 2
└─ preco_unitario: 25.00
```

---

## Validação de Integridade

**Constraint CHECK na tabela de itens:**
```sql
ALTER TABLE cardapio.pedidos_itens
ADD CONSTRAINT chk_item_tipo_unico
CHECK (
  (produto_cod_barras IS NOT NULL AND combo_id IS NULL AND receita_id IS NULL) OR
  (produto_cod_barras IS NULL AND combo_id IS NOT NULL AND receita_id IS NULL) OR
  (produto_cod_barras IS NULL AND combo_id IS NULL AND receita_id IS NOT NULL)
);
```

**Garante que:**
- Apenas um tipo de item por linha
- Não permite múltiplos tipos simultaneamente
- Não permite todos NULL

---

## Índices Recomendados

```sql
-- Pedidos
CREATE INDEX idx_pedidos_empresa_tipo_status 
ON cardapio.pedidos(empresa_id, tipo_pedido, status);

CREATE INDEX idx_pedidos_numero 
ON cardapio.pedidos(empresa_id, numero_pedido);

-- Itens
CREATE INDEX idx_pedidos_itens_pedido 
ON cardapio.pedidos_itens(pedido_id);

CREATE INDEX idx_pedidos_itens_produto 
ON cardapio.pedidos_itens(produto_cod_barras) 
WHERE produto_cod_barras IS NOT NULL;

CREATE INDEX idx_pedidos_itens_combo 
ON cardapio.pedidos_itens(combo_id) 
WHERE combo_id IS NOT NULL;

CREATE INDEX idx_pedidos_itens_receita 
ON cardapio.pedidos_itens(receita_id) 
WHERE receita_id IS NOT NULL;

-- Histórico
CREATE INDEX idx_pedidos_historico_pedido 
ON cardapio.pedidos_historico(pedido_id, created_at);
```

---

## Fluxo de Migração

```
1. Criar novos modelos
   ↓
2. Criar migration Alembic (criar tabelas)
   ↓
3. Executar script de migração de dados
   ↓
4. Validar integridade dos dados
   ↓
5. Atualizar código (serviços, schemas, routers)
   ↓
6. Testes
   ↓
7. Deploy
   ↓
8. Remover tabelas antigas (após validação)
```

