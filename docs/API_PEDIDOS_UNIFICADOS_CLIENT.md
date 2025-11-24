# API de Pedidos Unificados - Client

## 📋 Resumo das Alterações

### O que mudou?

1. **Repositório Unificado**: Todos os pedidos (DELIVERY, MESA, BALCAO) agora usam o mesmo repositório `PedidoRepository`
2. **Modelo Unificado**: Todos os pedidos estão na tabela `pedidos.pedidos` com campo `tipo_pedido`
3. **Itens Unificados**: Itens podem ser produtos, receitas ou combos na mesma tabela `pedidos.pedidos_itens`
4. **Checkout Unificado**: Um único endpoint de checkout suporta todos os tipos de pedido

### Arquivos Removidos
- ❌ `app/api/pedidos/repositories/repo_pedidos_balcao.py`
- ❌ `app/api/pedidos/repositories/repo_pedidos_mesa.py`

### Arquivos Atualizados
- ✅ `app/api/pedidos/repositories/repo_pedidos.py` - Agora suporta todos os tipos de pedido
- ✅ `app/api/pedidos/services/service_pedidos_balcao.py` - Usa repositório unificado
- ✅ `app/api/pedidos/services/service_pedidos_mesa.py` - Usa repositório unificado

---

## 🔌 Endpoints Disponíveis

### Base URL
```
/api/pedidos/client
```

**Autenticação**: Requer token de cliente (via `get_cliente_by_super_token`)

---

## 💰 1. Preview do Checkout

Calcula o preview do checkout (subtotal, taxas, desconto, total) sem criar o pedido.

### Endpoint
```
POST /api/pedidos/client/checkout/preview
```

### Request Body
```json
{
  "tipo_pedido": "DELIVERY",  // "DELIVERY", "MESA" ou "BALCAO"
  "empresa_id": 1,
  "endereco_id": 10,  // Obrigatório para DELIVERY
  "tipo_entrega": "DELIVERY",  // Apenas para DELIVERY
  "origem": "APP",  // Apenas para DELIVERY: "WEB", "APP", "BALCAO"
  "mesa_codigo": 12,  // Opcional para MESA e BALCAO (código da mesa)
  "num_pessoas": 4,  // Opcional para MESA
  "cupom_id": null,
  "observacao_geral": "Sem cebola",
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "7891234567890",
        "quantidade": 2,
        "observacao": "Sem cebola",
        "adicionais": [
          {
            "adicional_id": 5,
            "quantidade": 1
          }
        ]
      }
    ],
    "receitas": [
      {
        "receita_id": 8,
        "quantidade": 1,
        "observacao": null,
        "adicionais": []
      }
    ],
    "combos": [
      {
        "combo_id": 3,
        "quantidade": 1,
        "observacao": null,
        "adicionais": []
      }
    ]
  }
}
```

### Response (200 OK)
```json
{
  "subtotal": 47.30,
  "taxa_entrega": 5.00,
  "taxa_servico": 0.00,
  "valor_total": 52.30,
  "desconto": 0.00,
  "distancia_km": 2.5,
  "empresa_id": 1,
  "tempo_entrega_minutos": 45.0
}
```

---

## ✅ 2. Finalizar Checkout

Cria o pedido no banco de dados.

### Endpoint
```
POST /api/pedidos/client/checkout
```

### Request Body
Mesma estrutura do preview, com campos adicionais:

```json
{
  "tipo_pedido": "DELIVERY",  // "DELIVERY", "MESA" ou "BALCAO"
  "empresa_id": 1,
  "endereco_id": 10,  // Obrigatório para DELIVERY
  "tipo_entrega": "DELIVERY",
  "origem": "APP",
  "meio_pagamento_id": 1,
  "mesa_codigo": 12,  // Opcional para MESA e BALCAO
  "num_pessoas": 4,  // Opcional para MESA
  "cupom_id": null,
  "observacao_geral": "Sem cebola",
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "7891234567890",
        "quantidade": 2,
        "observacao": "Sem cebola",
        "adicionais": [
          {
            "adicional_id": 5,
            "quantidade": 1
          }
        ]
      }
    ],
    "receitas": [
      {
        "receita_id": 8,
        "quantidade": 1,
        "observacao": null,
        "adicionais": []
      }
    ],
    "combos": [
      {
        "combo_id": 3,
        "quantidade": 1,
        "observacao": null,
        "adicionais": []
      }
    ]
  }
}
```

### Response (201 Created)

**Para DELIVERY:**
```json
{
  "id": 123,
  "tipo_pedido": "DELIVERY",
  "numero_pedido": "DV-000123",
  "status": "I",
  "valor_total": 52.30,
  "itens": [
    {
      "id": 1,
      "produto_cod_barras": "7891234567890",
      "receita_id": null,
      "combo_id": null,
      "quantidade": 2,
      "preco_unitario": 15.90,
      "preco_total": 31.80,
      "observacao": "Sem cebola",
      "produto_descricao_snapshot": "Hambúrguer Artesanal"
    }
  ],
  "created_at": "2024-01-15T10:30:00"
}
```

**Para MESA:**
```json
{
  "id": 456,
  "tipo_pedido": "MESA",
  "numero_pedido": "M12-001",
  "status": "I",
  "valor_total": 78.00,
  "mesa_id": 12,
  "mesa": {
    "id": 12,
    "numero": "M12"
  },
  "num_pessoas": 4,
  "created_at": "2024-01-15T11:00:00"
}
```

**Para BALCAO:**
```json
{
  "id": 789,
  "tipo_pedido": "BALCAO",
  "numero_pedido": "BAL-000789",
  "status": "I",
  "valor_total": 32.50,
  "mesa_id": 10,
  "mesa": {
    "id": 10,
    "numero": "M10"
  },
  "created_at": "2024-01-15T12:00:00"
}
```

---

## 📋 3. Listar Pedidos do Cliente

Lista todos os pedidos do cliente (DELIVERY, MESA e BALCAO) mesclados.

### Endpoint
```
GET /api/pedidos/client/
```

### Query Parameters
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `skip` | int | ❌ Não | Número de registros para pular (padrão: 0) |
| `limit` | int | ❌ Não | Limite de registros (padrão: 50, máx: 200) |

### Exemplo de Request
```http
GET /api/pedidos/client/?skip=0&limit=50
Authorization: Bearer {client_token}
```

### Response (200 OK)
```json
[
  {
    "tipo_pedido": "DELIVERY",
    "criado_em": "2024-01-15T10:30:00",
    "atualizado_em": "2024-01-15T10:35:00",
    "status_codigo": "I",
    "status_descricao": "Em impressão",
    "numero_pedido": "123",
    "valor_total": 52.30,
    "delivery": {
      "id": 123,
      "status": "I",
      "valor_total": 52.30,
      // ... outros campos do pedido delivery
    },
    "mesa": null,
    "balcao": null
  },
  {
    "tipo_pedido": "MESA",
    "criado_em": "2024-01-15T11:00:00",
    "atualizado_em": "2024-01-15T11:05:00",
    "status_codigo": "I",
    "status_descricao": "Em impressão",
    "numero_pedido": "M12-001",
    "valor_total": 78.00,
    "delivery": null,
    "mesa": {
      "id": 456,
      "status": "I",
      "valor_total": 78.00,
      "mesa_id": 12,
      // ... outros campos do pedido mesa
    },
    "balcao": null
  },
  {
    "tipo_pedido": "BALCAO",
    "criado_em": "2024-01-15T12:00:00",
    "atualizado_em": "2024-01-15T12:05:00",
    "status_codigo": "I",
    "status_descricao": "Em impressão",
    "numero_pedido": "BAL-000789",
    "valor_total": 32.50,
    "delivery": null,
    "mesa": null,
    "balcao": {
      "id": 789,
      "status": "I",
      "valor_total": 32.50,
      "mesa_id": 10,
      // ... outros campos do pedido balcão
    }
  }
]
```

---

## ✏️ 4. Atualizar Itens do Pedido

Adiciona, atualiza ou remove itens de um pedido.

### Endpoint
```
PUT /api/pedidos/client/{pedido_id}/itens
```

### Path Parameters
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | int | ✅ Sim | ID do pedido |

### Request Body

**Adicionar Item:**
```json
{
  "acao": "adicionar",
  "produto_cod_barras": "7891234567890",
  "quantidade": 1,
  "observacao": "Sem cebola"
}
```

**Atualizar Item:**
```json
{
  "acao": "atualizar",
  "id": 1,
  "quantidade": 2,
  "observacao": "Com cebola"
}
```

**Remover Item:**
```json
{
  "acao": "remover",
  "id": 1
}
```

### Response (200 OK)
```json
{
  "id": 123,
  "status": "I",
  "valor_total": 68.20,
  "itens": [
    // ... lista atualizada de itens
  ]
}
```

---

## 📝 5. Editar Pedido

Edita informações gerais do pedido (endereço, meio de pagamento, cupom, etc.).

### Endpoint
```
PUT /api/pedidos/client/{pedido_id}/editar
```

### Path Parameters
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | int | ✅ Sim | ID do pedido |

### Request Body
```json
{
  "meio_pagamento_id": 2,
  "endereco_id": 11,
  "cupom_id": 5,
  "observacao_geral": "Nova observação",
  "troco_para": 100.00
}
```

**Todos os campos são opcionais** - apenas os campos enviados serão atualizados.

### Response (200 OK)
```json
{
  "id": 123,
  "meio_pagamento_id": 2,
  "endereco_id": 11,
  "cupom_id": 5,
  "observacao_geral": "Nova observação",
  "troco_para": 100.00,
  "valor_total": 52.30,
  // ... outros campos do pedido
}
```

---

## 🚫 6. Alterar Modo de Edição

⚠️ **DESATIVADO**: Este endpoint foi desativado. Alterações de status só são permitidas em endpoints de admin.

### Endpoint
```
PUT /api/pedidos/client/{pedido_id}/modo-edicao
```

### Response (403 Forbidden)
```json
{
  "detail": "Alteração de status de pedido é permitida apenas em endpoints de admin."
}
```

---

## 📝 Estrutura de Itens

### Item de Produto
```json
{
  "produto_cod_barras": "7891234567890",
  "quantidade": 2,
  "observacao": "Sem cebola",
  "adicionais": [
    {
      "adicional_id": 5,
      "quantidade": 1
    }
  ]
}
```

### Item de Receita
```json
{
  "receita_id": 8,
  "quantidade": 1,
  "observacao": null,
  "adicionais": [
    {
      "adicional_id": 3,
      "quantidade": 2
    }
  ]
}
```

### Item de Combo
```json
{
  "combo_id": 3,
  "quantidade": 1,
  "observacao": null,
  "adicionais": [
    {
      "adicional_id": 7,
      "quantidade": 1
    }
  ]
}
```

---

## 📝 Notas Importantes

### Tipos de Pedido

#### DELIVERY
- Requer: `endereco_id`, `tipo_entrega`, `origem`, `meio_pagamento_id`
- Opcional: `cupom_id`, `observacao_geral`
- Suporta: produtos, receitas e combos

#### MESA
- Requer: `empresa_id`, `mesa_codigo` (código da mesa, não ID)
- Opcional: `cliente_id`, `num_pessoas`, `observacoes`
- Suporta: produtos, receitas e combos

#### BALCAO
- Requer: `empresa_id`
- Opcional: `mesa_codigo`, `cliente_id`, `observacoes`
- Suporta: produtos, receitas e combos

### Validações
- Cliente só pode editar seus próprios pedidos
- Pedido deve existir
- Produto/receita/combo deve estar disponível e ativo
- Adicionais devem pertencer à empresa do pedido
- Para DELIVERY: endereço deve pertencer ao cliente

### Status do Pedido
- Cliente não pode alterar status diretamente
- Status é gerenciado apenas por admin
- Cliente pode editar pedidos em status editável (P, I, X)

---

## 🔗 Relacionados

- [API de Pedidos - Admin](./API_PEDIDOS_UNIFICADOS_ADMIN.md)
- [Plano de Migração](../PLANO_MIGRACAO_PEDIDOS_CENTRALIZADOS.md)

