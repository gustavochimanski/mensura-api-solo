# API de Pedidos Unificados - Admin

## 📋 Resumo das Alterações

### O que mudou?

1. **Repositório Unificado**: Todos os pedidos (DELIVERY, MESA, BALCAO) agora usam o mesmo repositório `PedidoRepository`
2. **Modelo Unificado**: Todos os pedidos estão na tabela `pedidos.pedidos` com campo `tipo_pedido`
3. **Itens Unificados**: Itens podem ser produtos, receitas ou combos na mesma tabela `pedidos.pedidos_itens`
4. **Histórico Unificado**: Histórico de todos os pedidos na tabela `pedidos.pedidos_historico`

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
/api/pedidos/admin
```

**Autenticação**: Requer token de admin (via `get_current_user`)

---

## 📊 1. Listar Pedidos (Kanban)

Lista todos os pedidos agrupados por tipo para visualização no Kanban.

### Endpoint
```
GET /api/pedidos/admin/kanban
```

### Query Parameters
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `date_filter` | date | ✅ Sim | Data no formato YYYY-MM-DD |
| `empresa_id` | int | ✅ Sim | ID da empresa (deve ser > 0) |
| `limit` | int | ❌ Não | Limite de pedidos por categoria (padrão: 500, máx: 1000) |

### Exemplo de Request
```http
GET /api/pedidos/admin/kanban?date_filter=2024-01-15&empresa_id=1&limit=500
Authorization: Bearer {admin_token}
```

### Response (200 OK)
```json
{
  "delivery": [
    {
      "id": 123,
      "status": "I",
      "cliente": {
        "id": 45,
        "nome": "João Silva",
        "telefone": "11999999999"
      },
      "valor_total": 45.90,
      "data_criacao": "2024-01-15T10:30:00",
      "observacao_geral": "Entregar na portaria",
      "endereco": "Rua Exemplo, 123 - São Paulo/SP",
      "meio_pagamento": {
        "id": 1,
        "nome": "Dinheiro",
        "tipo": "DINHEIRO",
        "ativo": true
      },
      "entregador": {
        "id": 5,
        "nome": "Carlos"
      },
      "pagamento": {
        "status": "PAGO",
        "esta_pago": true,
        "valor": 45.90
      },
      "tipo_pedido": "DELIVERY",
      "numero_pedido": "DV-000123"
    }
  ],
  "balcao": [
    {
      "id": 456,
      "status": "I",
      "cliente": {
        "id": 46,
        "nome": "Maria Santos"
      },
      "valor_total": 32.50,
      "data_criacao": "2024-01-15T11:00:00",
      "tipo_pedido": "BALCAO",
      "numero_pedido": "BAL-000456",
      "mesa_id": 10,
      "mesa_numero": "M10"
    }
  ],
  "mesas": [
    {
      "id": 789,
      "status": "I",
      "cliente": {
        "id": 47,
        "nome": "Pedro Costa"
      },
      "valor_total": 78.00,
      "data_criacao": "2024-01-15T12:00:00",
      "tipo_pedido": "MESA",
      "numero_pedido": "M12-001",
      "mesa_id": 12,
      "mesa_numero": "M12"
    }
  ]
}
```

---

## 🔍 2. Buscar Pedido por ID

Busca um pedido específico com todas as informações completas.

### Endpoint
```
GET /api/pedidos/admin/{pedido_id}
```

### Path Parameters
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | int | ✅ Sim | ID do pedido (deve ser > 0) |

### Exemplo de Request
```http
GET /api/pedidos/admin/123
Authorization: Bearer {admin_token}
```

### Response (200 OK)
```json
{
  "id": 123,
  "tipo_pedido": "DELIVERY",
  "numero_pedido": "DV-000123",
  "status": "I",
  "empresa_id": 1,
  "cliente_id": 45,
  "cliente": {
    "id": 45,
    "nome": "João Silva",
    "telefone": "11999999999"
  },
  "endereco_id": 10,
  "endereco": {
    "id": 10,
    "logradouro": "Rua Exemplo",
    "numero": "123",
    "bairro": "Centro",
    "cidade": "São Paulo",
    "estado": "SP",
    "cep": "01234567"
  },
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
      "produto_descricao_snapshot": "Hambúrguer Artesanal",
      "adicionais_snapshot": [
        {
          "adicional_id": 5,
          "nome": "Bacon Extra",
          "quantidade": 1,
          "preco_unitario": 3.50,
          "total": 3.50
        }
      ]
    },
    {
      "id": 2,
      "produto_cod_barras": null,
      "receita_id": 8,
      "combo_id": null,
      "quantidade": 1,
      "preco_unitario": 12.00,
      "preco_total": 12.00,
      "observacao": null,
      "produto_descricao_snapshot": "Pizza Margherita"
    }
  ],
  "subtotal": 47.30,
  "desconto": 0.00,
  "taxa_entrega": 5.00,
  "taxa_servico": 0.00,
  "valor_total": 52.30,
  "meio_pagamento_id": 1,
  "meio_pagamento": {
    "id": 1,
    "nome": "Dinheiro",
    "tipo": "DINHEIRO"
  },
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:35:00"
}
```

---

## 📜 3. Obter Histórico do Pedido

Obtém o histórico completo de alterações de um pedido.

### Endpoint
```
GET /api/pedidos/admin/{pedido_id}/historico
```

### Path Parameters
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | int | ✅ Sim | ID do pedido (deve ser > 0) |

### Exemplo de Request
```http
GET /api/pedidos/admin/123/historico
Authorization: Bearer {admin_token}
```

### Response (200 OK)
```json
{
  "pedido_id": 123,
  "historicos": [
    {
      "id": 1,
      "pedido_id": 123,
      "status": "I",
      "status_anterior": "P",
      "status_novo": "I",
      "tipo_operacao": "STATUS_ALTERADO",
      "descricao": "Status atualizado para I",
      "motivo": "Pendente → Em impressão",
      "observacoes": null,
      "criado_em": "2024-01-15T10:35:00",
      "criado_por": "admin",
      "usuario_id": 1,
      "cliente_id": null,
      "ip_origem": "192.168.1.1",
      "user_agent": "Mozilla/5.0..."
    },
    {
      "id": 2,
      "pedido_id": 123,
      "status": "P",
      "status_anterior": null,
      "status_novo": "P",
      "tipo_operacao": "PEDIDO_CRIADO",
      "descricao": "Pedido criado",
      "motivo": "Pedido criado",
      "criado_em": "2024-01-15T10:30:00",
      "criado_por": null,
      "usuario_id": null
    }
  ]
}
```

---

## 🔄 4. Atualizar Status do Pedido

Atualiza o status de um pedido.

### Endpoint
```
PUT /api/pedidos/admin/{pedido_id}/status
```

### Path Parameters
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | int | ✅ Sim | ID do pedido (deve ser > 0) |

### Query Parameters
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `novo_status` | enum | ✅ Sim | Novo status do pedido |

### Status Disponíveis
- `P` = PENDENTE
- `I` = EM IMPRESSÃO
- `R` = EM PREPARO
- `S` = SAIU PARA ENTREGA
- `E` = ENTREGUE
- `C` = CANCELADO
- `D` = EDITADO
- `X` = EM EDIÇÃO
- `A` = AGUARDANDO PAGAMENTO

### Exemplo de Request
```http
PUT /api/pedidos/admin/123/status?novo_status=R
Authorization: Bearer {admin_token}
```

### Response (200 OK)
```json
{
  "id": 123,
  "status": "R",
  "numero_pedido": "DV-000123",
  "valor_total": 52.30,
  // ... outros campos do pedido
}
```

---

## 🚴 5. Vincular Entregador

Vincula ou desvincula um entregador a um pedido de delivery.

### Endpoint
```
PUT /api/pedidos/admin/{pedido_id}/entregador
```

### Path Parameters
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | int | ✅ Sim | ID do pedido (deve ser > 0) |

### Query Parameters
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `entregador_id` | int \| null | ❌ Não | ID do entregador (null para desvincular) |

### Exemplo de Request - Vincular
```http
PUT /api/pedidos/admin/123/entregador?entregador_id=5
Authorization: Bearer {admin_token}
```

### Exemplo de Request - Desvincular
```http
PUT /api/pedidos/admin/123/entregador?entregador_id=null
Authorization: Bearer {admin_token}
```

### Response (200 OK)
```json
{
  "id": 123,
  "entregador_id": 5,
  "entregador": {
    "id": 5,
    "nome": "Carlos"
  },
  // ... outros campos do pedido
}
```

---

## 🚫 6. Desvincular Entregador

Desvincula o entregador atual de um pedido.

### Endpoint
```
DELETE /api/pedidos/admin/{pedido_id}/entregador
```

### Path Parameters
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | int | ✅ Sim | ID do pedido (deve ser > 0) |

### Exemplo de Request
```http
DELETE /api/pedidos/admin/123/entregador
Authorization: Bearer {admin_token}
```

### Response (200 OK)
```json
{
  "id": 123,
  "entregador_id": null,
  // ... outros campos do pedido
}
```

---

## 📝 Notas Importantes

### Tipos de Pedido
- **DELIVERY**: Pedidos de entrega (requer `endereco_id`, `tipo_entrega`, `origem`)
- **MESA**: Pedidos de mesa (requer `mesa_id`, opcional `num_pessoas`)
- **BALCAO**: Pedidos de balcão (opcional `mesa_id`)

### Itens do Pedido
Cada item pode ser:
- **Produto**: `produto_cod_barras` preenchido, `receita_id` e `combo_id` null
- **Receita**: `receita_id` preenchido, `produto_cod_barras` e `combo_id` null
- **Combo**: `combo_id` preenchido, `produto_cod_barras` e `receita_id` null

### Histórico
O histórico unificado suporta:
- Histórico simples (apenas mudança de status)
- Histórico detalhado (com `tipo_pedido` no banco, `tipo_operacao` na resposta JSON, `descricao`, `motivo`, etc.)

### Validações
- Pedido deve existir
- Entregador deve estar vinculado à empresa do pedido (ao vincular)
- Status deve ser válido
- Apenas um tipo de item por vez (produto OU receita OU combo)

---

## 🔗 Relacionados

- [API de Pedidos - Client](./API_PEDIDOS_UNIFICADOS_CLIENT.md)
- [Plano de Migração](../PLANO_MIGRACAO_PEDIDOS_CENTRALIZADOS.md)

