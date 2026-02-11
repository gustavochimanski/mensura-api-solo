# Documentação - Endpoints Client / Public (Combos)

Este documento descreve os endpoints públicos e client para consumir Combos com seções.

## Resumo
- Cada Combo possui preço base (`preco_total`) e uma lista de seções (`secoes`).
- Cada seção tem regras: `obrigatorio`, `quantitativo`, `minimo_itens`, `maximo_itens`.
- Itens da seção possuem `preco_incremental` (pode ser 0), `permite_quantidade`, `quantidade_min`/`quantidade_max`.

---

## Endpoints (Client)

Prefixo: `/api/catalogo/client/combos`

1) GET `/` — Listar combos (Client)
- Query params:
  - `cod_empresa` (int, obrigatório)
  - `page` (int, default=1)
  - `limit` (int, default=30)
  - `search` (string, opcional)
- Resposta: objeto paginado contendo `data: [ComboDTO]`, `total`, `page`, `limit`, `has_more`.

2) GET `/{combo_id}` — Obter combo (Client)
- Path: `combo_id` (int)
- Resposta: `ComboDTO` com `secoes` e `secoes.itens` (cada item contém `id`, `produto_cod_barras` ou `receita_id`, `preco_incremental`, `permite_quantidade`, `quantidade_min`, `quantidade_max`, `ordem`).

Exemplo (resposta simplificada de `ComboDTO.secoes`):
```json
[
  {
    "id": 10,
    "titulo": "Escolha uma Bebida",
    "descricao": "Bebidas disponíveis",
    "obrigatorio": true,
    "quantitativo": false,
    "minimo_itens": 1,
    "maximo_itens": 1,
    "ordem": 0,
    "itens": [
      {
        "id": 55,
        "produto_cod_barras": "7891234567890",
        "receita_id": null,
        "preco_incremental": 0.0,
        "permite_quantidade": false,
        "quantidade_min": 1,
        "quantidade_max": 1,
        "ordem": 0
      },
      {
        "id": 56,
        "produto_cod_barras": null,
        "receita_id": 12,
        "preco_incremental": 2.0,
        "permite_quantidade": false,
        "quantidade_min": 1,
        "quantidade_max": 1,
        "ordem": 1
      }
    ]
  }
]
```

---

## Endpoint (Public)

Prefixo: `/api/catalogo/public/combos`

1) GET `/{combo_id}` — Obter combo público
- Path: `combo_id` (int)
- Resposta: versão pública/compacta do combo (inclui `secoes` e `secoes.itens` com `preco_incremental`).
- Uso: front público sem autenticação.

---

## Checkout — Como enviar seleção de combo

No payload do checkout (FinalizarPedidoRequest), o combo pode ser enviado assim (novo formato `secoes`):

Exemplo:
```json
{
  "empresa_id": 1,
  "produtos": {
    "combos": [
      {
        "combo_id": 123,
        "quantidade": 2,
        "complementos": [],            // complementos tradicionais (se aplicam)
        "secoes": [
          {
            "secao_id": 10,
            "itens": [
              {"id": 55, "quantidade": 1},
              {"id": 56, "quantidade": 0}
            ]
          },
          {
            "secao_id": 11,
            "itens": [
              {"id": 60, "quantidade": 2}
            ]
          }
        ]
      }
    ]
  }
}
```

Regras aplicadas pelo backend no checkout:
- Para cada seção marcada `obrigatorio=true`, é validado que foram selecionados pelo menos `minimo_itens`.
- A quantidade total de itens selecionados por seção deve ficar entre `minimo_itens` e `maximo_itens`.
- Se item tem `permite_quantidade=false`, `quantidade` do item deve ser 1; caso contrário é validada entre `quantidade_min` e `quantidade_max`.
- Cálculo de preço do combo:
  preco_total_combo = preco_base_combo + sum(preco_incremental_item * qtd_item * qtd_combo)
  (os incrementais multiplicam pela quantidade do item selecionado e pela quantidade do combo).

Resposta de erro: 400 com mensagem detalhando a validação (ex.: seção obrigatória não selecionada, item inexistente, quantidade fora do permitido).

---

## Observações
- O formato legado de combos (`itens` simples) permanece compatível, mas recomenda-se usar `secoes`.
- Se precisar que o backend persista as seleções de seções no banco (para impressão/historico), informe que eu adiciono a persistência no schema `pedidos`.

