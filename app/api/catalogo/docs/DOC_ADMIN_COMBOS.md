# Documentação - Endpoints Admin (Combos)

Prefixo: `/api/catalogo/admin/combos` (autenticado - requer token de admin)

## Endpoints Admin

1) GET `/` — Listar combos (Admin)
- Query params:
  - `cod_empresa` (int, obrigatório)
  - `page` (int, default=1)
  - `limit` (int, default=30)
  - `search` (string, opcional)
- Resposta: `ListaCombosResponse` com `data: [ComboDTO]`.

2) GET `/{combo_id}` — Obter combo
- Path: `combo_id` (int)
- Retorna `ComboDTO` com `secoes` e `secoes.itens`.

3) POST `/` — Criar combo
- multipart/form-data:
  - `empresa_id` (int, obrigatório)
  - `titulo` (string)
  - `descricao` (string)
  - `preco_total` (decimal, preço base do combo)
  - `ativo` (bool)
  - `secoes` (string, JSON) — array de seções (ver exemplo abaixo)
  - `imagem` (file, opcional)
- Retorna: 201 Created com `ComboDTO`.

4) PUT `/{combo_id}` — Atualizar combo
- multipart/form-data (todos opcionais):
  - `titulo`, `descricao`, `preco_total`, `ativo`
  - `secoes` (string JSON) — se enviado, SUBSTITUI todas as seções existentes
  - `imagem` (file, opcional)
- Retorna: `ComboDTO` atualizado.

5) PUT `/{combo_id}/imagem` — Atualizar imagem
- multipart/form-data:
  - `cod_empresa` (int) — valida propriedade
  - `imagem` (file, obrigatória)
- Faz upload para MinIO e atualiza URL no combo.

6) DELETE `/{combo_id}` — Deletar combo
- Valida se o combo não está referenciado por itens de pedido (não permite exclusão se referenciado).
- Retorno: 204 No Content em sucesso.

---

## Estrutura do campo `secoes` (JSON usado em POST/PUT)

Array de seções. Cada seção:
- `titulo` (string)
- `descricao` (string, opcional)
- `obrigatorio` (bool) — se true, cliente deve selecionar pelo menos `minimo_itens`
- `quantitativo` (bool) — se true, permite selecionar múltiplos adicionais com quantidades
- `minimo_itens` (int)
- `maximo_itens` (int)
- `ordem` (int, opcional)
- `itens` (array) — itens da seção, cada um:
  - `produto_cod_barras` (string) OU `receita_id` (int) — exatamente um deve ser fornecido
  - `preco_incremental` (decimal >= 0) — pode ser 0
  - `permite_quantidade` (bool)
  - `quantidade_min` (int)
  - `quantidade_max` (int)
  - `ordem` (int, opcional)

Exemplo de payload `secoes` (envie COMO string JSON no multipart):
```json
[
  {
    "titulo": "Bebida (obrigatório)",
    "descricao": "Escolha 1 bebida",
    "obrigatorio": true,
    "quantitativo": false,
    "minimo_itens": 1,
    "maximo_itens": 1,
    "ordem": 0,
    "itens": [
      {
        "produto_cod_barras": "7891234567890",
        "preco_incremental": 0.00,
        "permite_quantidade": false,
        "quantidade_min": 1,
        "quantidade_max": 1,
        "ordem": 0
      },
      {
        "receita_id": 12,
        "preco_incremental": 2.00,
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

## Validações aplicadas no Admin (ao criar/atualizar)
- `empresa_id` deve existir.
- Cada seção deve ter ao menos 1 item.
- Em cada item, exatamente um de (`produto_cod_barras`, `receita_id`) deve ser informado.
- `preco_incremental` >= 0.
- Se `permite_quantidade` == false então `quantidade_min` e `quantidade_max` devem ser igual a 1.
- `quantidade_min` <= `quantidade_max`.
- Ao atualizar com `secoes` o conjunto anterior é substituído (DELETE + INSERT transacional).

---

## Observações para DevOps / Migrations
- Models adicionados:
  - `catalogo.combo_secoes`
  - `catalogo.combo_secoes_itens`
- É necessário criar migration Alembic para adicionar estas tabelas ao banco antes de rodar em produção.

Se quiser, eu gero a migration (SQL) para você aplicar.

