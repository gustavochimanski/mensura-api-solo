# Documentação Frontend — Landing Page Store

Este documento descreve como o frontend deve montar a **Landing Page Store** usando as vitrines do tipo **landingpage_store** (sem vínculo com categoria).

## Visão geral

- As vitrines da landing page são armazenadas em `cardapio.vitrines_landingpage_store`.
- Elas têm o **mesmo comportamento** das vitrines normais (título, slug, ordem, is_home e vínculos com produtos/combos/receitas),
  porém **não aceitam vínculo com categoria**.

## Endpoint público (montar página)

### Buscar dados completos para montar a landing page

- **GET** `/api/cardapio/public/home/landingpage-store`
- **Query**:
  - `empresa_id` (obrigatório): number
  - `is_home` (opcional, default `false`): boolean  
    - se `true`, retorna apenas vitrines com `is_home=true`
- **Resposta**: `LandingPageStoreResponse`

Estrutura:

```json
{
  "vitrines": [
    {
      "id": 1,
      "titulo": "Destaques",
      "slug": "destaques",
      "ordem": 1,
      "is_home": true,
      "cod_categoria": null,
      "href_categoria": null,
      "produtos": [],
      "combos": [],
      "receitas": []
    }
  ]
}
```

> Observação: `cod_categoria` e `href_categoria` sempre virão `null` neste endpoint.

## CRUD Admin (configurar vitrines da landing)

Os endpoints de vitrines admin existentes foram estendidos com o parâmetro **query** `landingpage_true`.

- Se `landingpage_true=false` (padrão): opera em `vitrines_dv` (com categoria opcional).
- Se `landingpage_true=true`: opera em `vitrines_landingpage_store` (**sem categoria**).

> Regra: quando `landingpage_true=true`, **não envie `cod_categoria`** (retorna 400).

### Exemplos rápidos

Criar vitrine landing:

`POST /api/cardapio/admin/vitrines?landingpage_true=true`

```json
{
  "empresa_id": 1,
  "titulo": "Vitrine Landing",
  "is_home": true
}
```

Vincular produto:

`POST /api/cardapio/admin/vitrines/{vitrine_id}/vincular?landingpage_true=true`

```json
{
  "empresa_id": 1,
  "cod_barras": "7890000000000"
}
```

