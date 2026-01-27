# Documentação Frontend — Parceiros e Banners

Esta documentação descreve os endpoints públicos/admin de **Parceiros** e **Banners de Parceiro**, incluindo a mudança do campo de destino do banner.

## Mudança importante (breaking change)

- **Removido**: `redireciona_categoria` (não existe mais e não há mais redirecionamento automático para categoria).
- **Adicionado**: `landingpage_store` (**boolean**: `true` ou `false`).

### Regras de destino do banner (frontend)

- Se `landingpage_store = true`: o frontend deve **navegar para a landing page da store** (rota interna definida pelo frontend).
- Se `landingpage_store = false`: o frontend pode usar `href_destino` (que é derivado de `link_redirecionamento`) para navegação.
- Observação: o backend **não monta mais** `href_destino` usando categoria. Agora:
  - `href_destino = link_redirecionamento` quando houver link
  - caso contrário `href_destino = "#"`

## Modelos (DTOs)

### `BannerParceiroOut`

Campos relevantes:
- `id`: number
- `nome`: string
- `ativo`: boolean
- `tipo_banner`: string (`"V"` ou `"H"`)
- `imagem`: string | null
- `categoria_id`: number | null (pode existir, mas **não é usada** para redirecionamento)
- `link_redirecionamento`: string | null
- `landingpage_store`: boolean
- `href_destino`: string (ver regras acima)

Exemplo:

```json
{
  "id": 10,
  "nome": "Banner Promo",
  "ativo": true,
  "tipo_banner": "H",
  "imagem": "https://.../banners/abc.png",
  "categoria_id": null,
  "link_redirecionamento": "https://parceiro.com/oferta",
  "landingpage_store": false,
  "href_destino": "https://parceiro.com/oferta"
}
```

## Endpoints Públicos

### Listar parceiros

- **GET** `/api/cadastros/public/parceiros/`
- **Resposta**: `ParceiroOut[]` (inclui `banners`)

### Listar banners (para exibição no app/site)

- **GET** `/api/cadastros/public/parceiros/banners`
- **Query**:
  - `parceiro_id` (opcional): number
- **Resposta**: `BannerParceiroOut[]`

### Parceiro completo (banners + cupons)

- **GET** `/api/cadastros/public/parceiros/{parceiro_id}/full`
- **Resposta**: `ParceiroCompletoOut` (inclui `banners: BannerParceiroOut[]`)

## Endpoints Admin

> Todos os endpoints admin exigem autenticação de admin (Bearer Token).

### CRUD de parceiros

- **GET** `/api/cadastros/admin/parceiros/`
- **GET** `/api/cadastros/admin/parceiros/{parceiro_id}`
- **POST** `/api/cadastros/admin/parceiros/` (JSON `ParceiroIn`)
- **PUT** `/api/cadastros/admin/parceiros/{parceiro_id}` (JSON `ParceiroIn`)
- **DELETE** `/api/cadastros/admin/parceiros/{parceiro_id}`

### Criar banner (com upload de imagem)

- **POST** `/api/cadastros/admin/parceiros/banners`
- **Content-Type**: `multipart/form-data`
- **Campos**:
  - `nome` (string, obrigatório)
  - `tipo_banner` (string, obrigatório) — `"V"` ou `"H"`
  - `ativo` (boolean, obrigatório) — envie como `"true"`/`"false"`
  - `parceiro_id` (number, obrigatório)
  - `categoria_id` (number, opcional)
  - `link_redirecionamento` (string, opcional)
  - `landingpage_store` (boolean, obrigatório) — envie como `"true"`/`"false"`
  - `imagem` (file, opcional)
- **Resposta**: `BannerParceiroOut`

### Atualizar banner

- **PUT** `/api/cadastros/admin/parceiros/banners/{banner_id}`
- **Body (JSON)**: `BannerParceiroIn`
  - Observação: o schema atual exige os campos do `BannerParceiroIn` completos (incluindo `landingpage_store`).
- **Resposta**: `BannerParceiroOut`

### Deletar banner

- **DELETE** `/api/cadastros/admin/parceiros/banners/{banner_id}`
- **Status**: 204

