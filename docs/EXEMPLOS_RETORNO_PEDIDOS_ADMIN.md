# Exemplos de Retorno - GET Pedidos Admin

Este documento apresenta exemplos de retorno dos endpoints GET para buscar informações de pedidos admin (balcão, mesa e delivery).

## 1. Pedido Unificado (Balcão, Mesa ou Delivery)

**Endpoint:** `GET /api/pedidos/admin/{pedido_id}`

**Schema de Retorno:** `PedidoOut`

### Exemplo 1: Pedido de Mesa

```json
{
  "id": 123,
  "tipo_pedido": "MESA",
  "empresa_id": 1,
  "numero_pedido": "MESA-001",
  "status": "PREPARANDO",
  "status_descricao": "Em Preparo",
  "status_cor": "#FFA500",
  "mesa_id": 5,
  "cliente_id": 10,
  "endereco_id": null,
  "meio_pagamento_id": 2,
  "cupom_id": null,
  "observacoes": "Sem cebola",
  "observacao_geral": null,
  "num_pessoas": 4,
  "troco_para": null,
  "subtotal": 85.50,
  "desconto": 0.00,
  "taxa_entrega": 0.00,
  "taxa_servico": 0.00,
  "valor_total": 85.50,
  "created_at": "2024-01-15T14:30:00",
  "updated_at": "2024-01-15T14:35:00",
  "produtos": {
    "itens": [
      {
        "item_id": 456,
        "produto_cod_barras": "7891234567890",
        "descricao": "Hambúrguer Artesanal",
        "imagem": "https://example.com/hamburger.jpg",
        "quantidade": 2,
        "preco_unitario": 25.00,
        "observacao": "Sem cebola",
        "adicionais": [
          {
            "adicional_id": 1,
            "nome": "Queijo Extra",
            "quantidade": 1,
            "preco_unitario": 3.00,
            "total": 3.00
          }
        ]
      },
      {
        "item_id": 457,
        "produto_cod_barras": "7891234567891",
        "descricao": "Batata Frita",
        "imagem": "https://example.com/batata.jpg",
        "quantidade": 1,
        "preco_unitario": 15.50,
        "observacao": null,
        "adicionais": []
      }
    ],
    "receitas": [
      {
        "item_id": 458,
        "receita_id": 10,
        "nome": "Hambúrguer Artesanal Especial",
        "quantidade": 1,
        "preco_unitario": 30.00,
        "observacao": null,
        "adicionais": []
      }
    ],
    "combos": [
      {
        "combo_id": 3,
        "nome": "Combo Executivo",
        "quantidade": 1,
        "preco_unitario": 20.00,
        "observacao": null,
        "adicionais": []
      }
    ]
  }
}
```

### Exemplo 2: Pedido de Balcão

```json
{
  "id": 124,
  "tipo_pedido": "BALCAO",
  "empresa_id": 1,
  "numero_pedido": "BAL-001",
  "status": "PENDENTE",
  "status_descricao": "Pendente",
  "status_cor": "#FF0000",
  "mesa_id": null,
  "cliente_id": 11,
  "endereco_id": null,
  "meio_pagamento_id": 1,
  "cupom_id": null,
  "observacoes": "Para viagem",
  "observacao_geral": null,
  "num_pessoas": null,
  "troco_para": 50.00,
  "subtotal": 35.00,
  "desconto": 0.00,
  "taxa_entrega": 0.00,
  "taxa_servico": 0.00,
  "valor_total": 35.00,
  "created_at": "2024-01-15T15:00:00",
  "updated_at": "2024-01-15T15:00:00",
  "produtos": {
    "itens": [
      {
        "item_id": 459,
        "produto_cod_barras": "7891234567892",
        "descricao": "Pizza Margherita",
        "imagem": "https://example.com/pizza-margherita.jpg",
        "quantidade": 1,
        "preco_unitario": 35.00,
        "observacao": "Para viagem",
        "adicionais": []
      }
    ],
    "receitas": [],
    "combos": []
  }
}
```

### Exemplo 3: Pedido de Delivery

```json
{
  "id": 125,
  "tipo_pedido": "DELIVERY",
  "empresa_id": 1,
  "numero_pedido": "DEL-001",
  "status": "SAIU_PARA_ENTREGA",
  "status_descricao": "Saiu para Entrega",
  "status_cor": "#0000FF",
  "mesa_id": null,
  "cliente_id": 12,
  "endereco_id": 20,
  "entregador_id": 5,
  "meio_pagamento_id": 3,
  "cupom_id": 1,
  "tipo_entrega": "DELIVERY",
  "origem": "APP",
  "observacoes": null,
  "observacao_geral": "Deixar na portaria",
  "num_pessoas": null,
  "troco_para": null,
  "subtotal": 120.00,
  "desconto": 10.00,
  "taxa_entrega": 5.00,
  "taxa_servico": 2.00,
  "valor_total": 117.00,
  "previsao_entrega": "2024-01-15T16:00:00",
  "distancia_km": 3.5,
  "acertado_entregador": true,
  "acertado_entregador_em": "2024-01-15T15:30:00",
  "created_at": "2024-01-15T14:00:00",
  "updated_at": "2024-01-15T15:45:00",
  "produtos": {
    "itens": [
      {
        "item_id": 460,
        "produto_cod_barras": "7891234567893",
        "descricao": "Pizza Calabresa",
        "imagem": "https://example.com/pizza-calabresa.jpg",
        "quantidade": 2,
        "preco_unitario": 45.00,
        "observacao": "Bem assada",
        "adicionais": [
          {
            "adicional_id": 1,
            "nome": "Borda Recheada",
            "quantidade": 1,
            "preco_unitario": 5.00,
            "total": 5.00
          }
        ]
      },
      {
        "item_id": 461,
        "produto_cod_barras": "7891234567894",
        "descricao": "Refrigerante 2L",
        "imagem": "https://example.com/refrigerante.jpg",
        "quantidade": 1,
        "preco_unitario": 10.00,
        "observacao": null,
        "adicionais": []
      }
    ],
    "receitas": [],
    "combos": [
      {
        "combo_id": 5,
        "nome": "Combo Família",
        "quantidade": 1,
        "preco_unitario": 20.00,
        "observacao": null,
        "adicionais": []
      }
    ]
  }
}
```

---

## 2. Pedido de Mesa (Endpoint Específico)

**Endpoint:** `GET /api/mesas/admin/pedidos/{pedido_id}`

**Schema de Retorno:** `PedidoMesaOut`

```json
{
  "id": 123,
  "empresa_id": 1,
  "numero_pedido": "MESA-001",
  "mesa_id": 5,
  "cliente_id": 10,
  "num_pessoas": 4,
  "status": "PREPARANDO",
  "status_descricao": "Em Preparo",
  "observacoes": "Sem cebola",
  "valor_total": 85.50,
  "created_at": "2024-01-15T14:30:00",
  "updated_at": "2024-01-15T14:35:00",
  "produtos": {
    "itens": [
      {
        "item_id": 456,
        "produto_cod_barras": "7891234567890",
        "descricao": "Hambúrguer Artesanal",
        "imagem": "https://example.com/hamburger.jpg",
        "quantidade": 2,
        "preco_unitario": 25.00,
        "observacao": "Sem cebola",
        "adicionais": [
          {
            "adicional_id": 1,
            "nome": "Queijo Extra",
            "quantidade": 1,
            "preco_unitario": 3.00,
            "total": 3.00
          }
        ]
      },
      {
        "item_id": 457,
        "produto_cod_barras": "7891234567891",
        "descricao": "Batata Frita",
        "imagem": "https://example.com/batata.jpg",
        "quantidade": 1,
        "preco_unitario": 15.50,
        "observacao": null,
        "adicionais": []
      }
    ],
    "receitas": [
      {
        "item_id": 458,
        "receita_id": 10,
        "nome": "Hambúrguer Artesanal Especial",
        "quantidade": 1,
        "preco_unitario": 30.00,
        "observacao": null,
        "adicionais": []
      }
    ],
    "combos": [
      {
        "combo_id": 3,
        "nome": "Combo Executivo",
        "quantidade": 1,
        "preco_unitario": 20.00,
        "observacao": null,
        "adicionais": []
      }
    ]
  }
}
```

---

## 3. Pedido de Delivery/Balcão (Cardápio - Completo)

**Endpoint:** `GET /api/cardapio/admin/pedidos/{pedido_id}`

**Schema de Retorno:** `PedidoResponseCompletoTotal`

### Exemplo: Pedido de Delivery Completo

```json
{
  "id": 125,
  "status": "S",
  "cliente": {
    "id": 12,
    "nome": "João Silva",
    "telefone": "11999999999",
    "email": "joao@example.com",
    "cpf": "12345678900",
    "data_nascimento": "1990-01-01",
    "ativo": true
  },
  "endereco": {
    "endereco_selecionado": {
      "id": 20,
      "rua": "Rua das Flores",
      "numero": "123",
      "complemento": "Apto 45",
      "bairro": "Centro",
      "cidade": "São Paulo",
      "estado": "SP",
      "cep": "01234567",
      "referencia": "Próximo ao mercado"
    },
    "outros_enderecos": []
  },
  "empresa": {
    "id": 1,
    "nome": "Restaurante Exemplo",
    "cnpj": "12345678000190",
    "telefone": "1133334444"
  },
  "entregador": {
    "id": 5,
    "nome": "Carlos Entregador",
    "telefone": "1188887777",
    "veiculo": "Moto",
    "placa": "ABC1234",
    "ativo": true
  },
  "meio_pagamento": {
    "id": 3,
    "nome": "Cartão de Crédito",
    "tipo": "CARTAO_CREDITO",
    "ativo": true
  },
  "cupom": {
    "id": 1,
    "codigo": "DESC10",
    "desconto_percentual": 10.0,
    "desconto_fixo": null,
    "valor_minimo": 50.00,
    "ativo": true
  },
  "transacao": {
    "id": 100,
    "status": "APROVADA",
    "valor": 117.00,
    "metodo": "CARTAO_CREDITO",
    "gateway": "MERCADO_PAGO",
    "provider_transaction_id": "MP-123456789"
  },
  "historicos": [
    {
      "id": 1,
      "pedido_id": 125,
      "status": "P",
      "motivo": "Pedido criado",
      "observacoes": null,
      "criado_em": "2024-01-15T14:00:00",
      "criado_por": "admin",
      "ip_origem": "192.168.1.1",
      "user_agent": "Mozilla/5.0..."
    },
    {
      "id": 2,
      "pedido_id": 125,
      "status": "R",
      "motivo": "Iniciado preparo",
      "observacoes": null,
      "criado_em": "2024-01-15T14:15:00",
      "criado_por": "cozinha",
      "ip_origem": "192.168.1.2",
      "user_agent": "Mozilla/5.0..."
    },
    {
      "id": 3,
      "pedido_id": 125,
      "status": "S",
      "motivo": "Saiu para entrega",
      "observacoes": "Entregador: Carlos",
      "criado_em": "2024-01-15T15:30:00",
      "criado_por": "admin",
      "ip_origem": "192.168.1.1",
      "user_agent": "Mozilla/5.0..."
    }
  ],
  "tipo_entrega": "DELIVERY",
  "origem": "APP",
  "subtotal": 120.00,
  "desconto": 10.00,
  "taxa_entrega": 5.00,
  "taxa_servico": 2.00,
  "valor_total": 117.00,
  "previsao_entrega": "2024-01-15T16:00:00",
  "distancia_km": 3.5,
  "observacao_geral": "Deixar na portaria",
  "troco_para": null,
  "endereco_snapshot": {
    "rua": "Rua das Flores",
    "numero": "123",
    "complemento": "Apto 45",
    "bairro": "Centro",
    "cidade": "São Paulo",
    "estado": "SP",
    "cep": "01234567"
  },
  "endereco_geography": "POINT(-46.6333 -23.5505)",
  "data_criacao": "2024-01-15T14:00:00",
  "data_atualizacao": "2024-01-15T15:45:00",
  "itens": [],
  "pagamento": {
    "status": "APROVADO",
    "esta_pago": true,
    "valor": 117.00,
    "atualizado_em": "2024-01-15T14:05:00",
    "meio_pagamento_id": 3,
    "meio_pagamento_nome": "Cartão de Crédito",
    "metodo": "CARTAO_CREDITO",
    "gateway": "MERCADO_PAGO",
    "provider_transaction_id": "MP-123456789"
  },
  "produtos": {
    "itens": [
      {
        "item_id": 460,
        "produto_cod_barras": "7891234567893",
        "descricao": "Pizza Calabresa",
        "imagem": "https://example.com/pizza-calabresa.jpg",
        "quantidade": 2,
        "preco_unitario": 45.00,
        "observacao": "Bem assada",
        "adicionais": [
          {
            "adicional_id": 1,
            "nome": "Borda Recheada",
            "quantidade": 1,
            "preco_unitario": 5.00,
            "total": 5.00
          },
          {
            "adicional_id": 2,
            "nome": "Bacon Extra",
            "quantidade": 2,
            "preco_unitario": 4.00,
            "total": 8.00
          }
        ]
      },
      {
        "item_id": 461,
        "produto_cod_barras": "7891234567894",
        "descricao": "Refrigerante 2L",
        "imagem": "https://example.com/refrigerante.jpg",
        "quantidade": 1,
        "preco_unitario": 10.00,
        "observacao": null,
        "adicionais": []
      }
    ],
    "receitas": [
      {
        "item_id": 462,
        "receita_id": 15,
        "nome": "Pizza Artesanal Especial",
        "quantidade": 1,
        "preco_unitario": 55.00,
        "observacao": "Bem assada",
        "adicionais": [
          {
            "adicional_id": 3,
            "nome": "Queijo Brie",
            "quantidade": 1,
            "preco_unitario": 8.00,
            "total": 8.00
          }
        ]
      }
    ],
    "combos": [
      {
        "combo_id": 5,
        "nome": "Combo Família",
        "quantidade": 1,
        "preco_unitario": 20.00,
        "observacao": null,
        "adicionais": []
      }
    ]
  }
}
```

### Exemplo: Pedido de Balcão Completo

```json
{
  "id": 124,
  "status": "P",
  "cliente": {
    "id": 11,
    "nome": "Maria Santos",
    "telefone": "11888888888",
    "email": "maria@example.com",
    "cpf": "98765432100",
    "data_nascimento": "1985-05-15",
    "ativo": true
  },
  "endereco": null,
  "empresa": {
    "id": 1,
    "nome": "Restaurante Exemplo",
    "cnpj": "12345678000190",
    "telefone": "1133334444"
  },
  "meio_pagamento": {
    "id": 1,
    "nome": "Dinheiro",
    "tipo": "DINHEIRO",
    "ativo": true
  },
  "cupom": null,
  "transacao": null,
  "historicos": [
    {
      "id": 4,
      "pedido_id": 124,
      "status": "P",
      "motivo": "Pedido criado no balcão",
      "observacoes": null,
      "criado_em": "2024-01-15T15:00:00",
      "criado_por": "atendente",
      "ip_origem": "192.168.1.3",
      "user_agent": "Mozilla/5.0..."
    }
  ],
  "origem": "BALCAO",
  "subtotal": 35.00,
  "desconto": 0.00,
  "taxa_entrega": 0.00,
  "taxa_servico": 0.00,
  "valor_total": 35.00,
  "observacao_geral": "Para viagem",
  "troco_para": 50.00,
  "endereco_snapshot": null,
  "endereco_geography": null,
  "data_criacao": "2024-01-15T15:00:00",
  "data_atualizacao": "2024-01-15T15:00:00",
  "itens": [],
  "pagamento": {
    "status": "PENDENTE",
    "esta_pago": false,
    "valor": null,
    "atualizado_em": null,
    "meio_pagamento_id": 1,
    "meio_pagamento_nome": "Dinheiro",
    "metodo": "DINHEIRO",
    "gateway": null,
    "provider_transaction_id": null
  },
  "produtos": {
    "itens": [
      {
        "item_id": 459,
        "produto_cod_barras": "7891234567892",
        "descricao": "Pizza Margherita",
        "imagem": "https://example.com/pizza-margherita.jpg",
        "quantidade": 1,
        "preco_unitario": 35.00,
        "observacao": "Para viagem",
        "adicionais": [
          {
            "adicional_id": 4,
            "nome": "Azeitona",
            "quantidade": 1,
            "preco_unitario": 2.00,
            "total": 2.00
          }
        ]
      }
    ],
    "receitas": [],
    "combos": []
  }
}
```

---

## Observações Importantes

1. **Status do Pedido:**
   - `P` = PENDENTE
   - `I` = EM IMPRESSÃO
   - `R` = EM PREPARO / PREPARANDO
   - `S` = SAIU PARA ENTREGA (apenas delivery)
   - `E` = ENTREGUE
   - `C` = CANCELADO
   - `D` = EDITADO
   - `X` = EM EDIÇÃO
   - `A` = AGUARDANDO PAGAMENTO

2. **Tipos de Pedido:**
   - `MESA` = Pedido de mesa
   - `BALCAO` = Pedido de balcão
   - `DELIVERY` = Pedido de delivery

3. **Campos Específicos:**
   - **Mesa:** `mesa_id`, `num_pessoas`
     - **NÃO retorna:** `entregador_id`, `tipo_entrega`, `distancia_km`, `acertado_entregador`, `acertado_entregador_em`, `previsao_entrega`
   - **Balcão:** `troco_para` (quando pagamento em dinheiro)
     - **NÃO retorna:** `entregador_id`, `tipo_entrega`, `distancia_km`, `acertado_entregador`, `acertado_entregador_em`, `previsao_entrega`
   - **Delivery:** `endereco_id`, `entregador_id`, `tipo_entrega`, `origem`, `previsao_entrega`, `distancia_km`, `acertado_entregador`, `acertado_entregador_em`

4. **Estrutura de Produtos (Checkout):**
   - Todos os produtos do pedido estão organizados no objeto `produtos` com três categorias:
     - **`itens`**: Lista de produtos normais (com `produto_cod_barras`)
     - **`receitas`**: Lista de receitas (com `receita_id`)
     - **`combos`**: Lista de combos (com `combo_id`)
   - Cada item/receita/combo pode ter uma lista de `adicionais` com:
     - `adicional_id`: ID do adicional
     - `nome`: Nome do adicional
     - `quantidade`: Quantidade do adicional
     - `preco_unitario`: Preço unitário do adicional
     - `total`: Total do adicional (quantidade × preço_unitario)

5. **Endpoints Disponíveis:**
   - `/api/pedidos/admin/{pedido_id}` - Pedido unificado (todos os tipos)
   - `/api/mesas/admin/pedidos/{pedido_id}` - Pedido de mesa específico
   - `/api/cardapio/admin/pedidos/{pedido_id}` - Pedido completo (delivery/balcão) com todas as informações

