# Padrão de Retorno de Pedidos - API Mensura

## 📋 Visão Geral

Este documento define o padrão obrigatório para **todos os endpoints GET que retornam pedidos** na API Mensura. Este padrão garante consistência e facilita o desenvolvimento de interfaces que consomem esses dados.

---

## 🎯 Objetivo

Garantir que **todos os endpoints GET de pedidos** retornem:
1. **Estrutura padronizada** com campo `produtos` contendo `itens`, `receitas` e `combos`
2. **Valor total calculado corretamente** incluindo receitas, combos e adicionais
3. **Compatibilidade com o schema de checkout** para facilitar integração

---

## 📦 Schema de Retorno Obrigatório

### Campo `produtos`

Todos os pedidos devem retornar um campo `produtos` do tipo `ProdutosPedidoOut` com a seguinte estrutura:

```python
{
    "produtos": {
        "itens": [
            {
                "item_id": int,
                "produto_cod_barras": str,
                "descricao": str | None,
                "imagem": str | None,
                "quantidade": int,
                "preco_unitario": float,
                "observacao": str | None,
                "adicionais": [
                    {
                        "adicional_id": int | None,
                        "nome": str | None,
                        "quantidade": int,
                        "preco_unitario": float,
                        "total": float
                    }
                ]
            }
        ],
        "receitas": [
            {
                "item_id": int | None,
                "receita_id": int,
                "nome": str | None,
                "quantidade": int,
                "preco_unitario": float,
                "observacao": str | None,
                "adicionais": [...]
            }
        ],
        "combos": [
            {
                "combo_id": int,
                "nome": str | None,
                "quantidade": int,
                "preco_unitario": float,
                "observacao": str | None,
                "adicionais": [...]
            }
        ]
    }
}
```

### Campo `valor_total`

O campo `valor_total` **DEVE** ser calculado incluindo:
- ✅ Soma de todos os `itens` (produtos normais) e seus adicionais
- ✅ Soma de todas as `receitas` e seus adicionais
- ✅ Soma de todos os `combos` e seus adicionais
- ✅ Subtração de descontos
- ✅ Adição de taxas (entrega, serviço, etc.)

**⚠️ IMPORTANTE:** O `valor_total` **NÃO** deve ser apenas o valor salvo no banco de dados. Deve ser **recalculado** considerando todos os componentes acima.

---

## 🔧 Implementação

### 1. Construção do Campo `produtos`

Use a função utilitária `build_produtos_out_from_items` do módulo `app.api.pedidos.utils.produtos_builder`:

```python
from app.api.pedidos.utils.produtos_builder import build_produtos_out_from_items

# No método que retorna o pedido
produtos_snapshot = getattr(pedido, "produtos_snapshot", None)
produtos = build_produtos_out_from_items(pedido.itens, produtos_snapshot)
```

### 2. Cálculo do `valor_total`

Use as funções de cálculo disponíveis nos repositórios ou serviços:

- **Pedidos de Delivery:** Use `_calcular_valor_total_delivery_com_receitas_combos()`
- **Pedidos de Mesa/Balcão:** Use `_calcular_valor_total_mesa_balcao_com_receitas_combos()` ou o método `_calc_total()` do repositório

**Exemplo:**

```python
# Para pedidos de delivery
valor_total = self._calcular_valor_total_delivery_com_receitas_combos(pedido)

# Para pedidos de mesa/balcão
valor_total = self._calcular_valor_total_mesa_balcao_com_receitas_combos(pedido)
```

---

## 📝 Endpoints que DEVEM seguir este padrão

### ✅ Já implementados:
- `GET /api/cardapio/admin/pedidos/{pedido_id}` (Delivery) - Retorna `PedidoResponseCompletoTotal`
- `GET /api/cardapio/client/pedidos/{pedido_id}` (Delivery) - Retorna `PedidoResponseSimplificado`

### 🔄 Devem ser atualizados:
- `GET /api/balcao/admin/pedidos/{pedido_id}` (Balcão)
- `GET /api/mesas/admin/pedidos/{pedido_id}` (Mesas)
- Qualquer outro endpoint GET que retorne informações de pedido

---

## 📚 Schemas de Referência

- `ProdutosPedidoOut` - Schema principal para o campo `produtos`
- `PedidoResponseCompletoTotal` - Schema de exemplo para pedidos completos
- `PedidoResponseSimplificado` - Schema de exemplo para pedidos simplificados

**Localização:** `app/api/cardapio/schemas/schema_pedido.py`

---

## ⚠️ Regras Importantes

1. **SEMPRE** retornar o campo `produtos` estruturado (mesmo que vazio)
2. **SEMPRE** recalcular `valor_total` ao construir a resposta (não confiar apenas no valor do banco)
3. **SEMPRE** incluir receitas e combos do `produtos_snapshot` no cálculo do valor total
4. **SEMPRE** incluir adicionais de itens, receitas e combos no cálculo do valor total

---

## 🔍 Verificação

Para verificar se um endpoint está seguindo o padrão:

1. ✅ O campo `produtos` existe na resposta?
2. ✅ O campo `produtos` tem `itens`, `receitas` e `combos`?
3. ✅ O `valor_total` inclui receitas, combos e adicionais?
4. ✅ Os adicionais estão estruturados corretamente?

---

## 📖 Exemplo Completo de Resposta

```json
{
    "id": 123,
    "numero_pedido": "BAL-000123",
    "status": "R",
    "valor_total": 45.90,
    "subtotal": 40.00,
    "desconto": 0.00,
    "taxa_servico": 5.90,
    "produtos": {
        "itens": [
            {
                "item_id": 1,
                "produto_cod_barras": "7891234567890",
                "descricao": "Hambúrguer Artesanal",
                "quantidade": 2,
                "preco_unitario": 15.00,
                "adicionais": [
                    {
                        "adicional_id": 5,
                        "nome": "Bacon Extra",
                        "quantidade": 2,
                        "preco_unitario": 3.00,
                        "total": 6.00
                    }
                ]
            }
        ],
        "receitas": [
            {
                "receita_id": 10,
                "nome": "Pizza Margherita",
                "quantidade": 1,
                "preco_unitario": 25.00,
                "adicionais": []
            }
        ],
        "combos": []
    },
    "itens": [...],  // Campo legado para compatibilidade
    "cliente": {...},
    "created_at": "2025-01-24T10:00:00Z"
}
```

---

**Última atualização:** Janeiro 2025  
**Mantido por:** Equipe de Desenvolvimento Mensura

