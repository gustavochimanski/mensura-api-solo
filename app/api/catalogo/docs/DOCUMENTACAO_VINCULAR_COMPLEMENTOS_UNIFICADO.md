# Documentação — Atualizar Produto + Vincular Complementos (Unificado)

## Resumo
A vinculação de complementos a um produto foi unificada no endpoint de atualização de produto.
Agora você pode atualizar os campos do produto e, opcionalmente, enviar uma configuração de complementos no mesmo request.

## Endpoint principal
- Método: PUT  
- URL: `/api/catalogo/admin/produtos/{cod_barras}`  
- Autenticação: Admin (dependência `get_current_user`)  
- Content-Type: `multipart/form-data` (suporta upload de imagem)

## Campos (form)
- `cod_empresa` (int) — obrigatório  
- `descricao` (string) — opcional  
- `preco_venda` (number) — opcional  
- `custo` (number) — opcional  
- `sku_empresa` (string) — opcional  
- `disponivel` (boolean) — opcional  
- `exibir_delivery` (boolean) — opcional  
- `ativo` (boolean) — opcional  
- `unidade_medida` (string) — opcional  
- `imagem` (file) — opcional  
- `complementos` (string, opcional) — JSON string com a configuração de vinculação

> Observação: `complementos` deve ser uma *string* contendo JSON (porque o request é multipart/form-data).

## Formato do campo `complementos`

Aceitamos dois formatos — escolha um:

### 1) Formato completo (recomendado)
Define configuração por complemento:

```json
{
  "configuracoes": [
    {
      "complemento_id": 1,
      "ordem": 0,
      "obrigatorio": false,
      "quantitativo": true,
      "minimo_itens": null,
      "maximo_itens": 5
    }
  ]
}
```

- Regras:
  - Se `quantitativo` for `false`, `minimo_itens` e `maximo_itens` serão forçados a `null`.
  - Campos `ordem` são opcionais (será usado índice se ausente).

### 2) Formato simples (compatibilidade)
Mantido para clientes antigos:
```json
{
  "complemento_ids": [1, 2],
  "ordens": [0, 1]
}
```

## Comportamento
- O endpoint primeiro atualiza o produto com os campos enviados.  
- Se `complementos` for fornecido:
  - É parseado como JSON e validado pelo schema `VincularComplementosProdutoRequest`.  
  - A vinculação é aplicada chamando internamente `ComplementoService.vincular_complementos_produto(cod_barras, req)`.  
  - Em caso de erro de validação ou de vinculação, o endpoint retorna 400 com detalhe do erro.
  - O update do produto já terá sido realizado — comportamento intencional (vinculação é um passo adicional).

## Respostas
- Sucesso (produto atualizado, vinculação OK ou não fornecida): retorna o mesmo `CriarNovoProdutoResponse` do update de produto (HTTP 200).  
- Erro de validação do JSON `complementos` ou dados de complementos: HTTP 400 com mensagem detalhada.  
- Erro interno: HTTP 500.

## Listagem de complementos por produto (rota unificada)
- Método: GET  
- URL: `/api/catalogo/admin/produtos/{cod_barras}/complementos`  
- Query params:
  - `apenas_ativos` (boolean, opcional, default true) — filtra apenas complementos ativos
- Observação: Este endpoint substitui o antigo `/api/catalogo/admin/complementos/produto/{cod_barras}`. Clientes devem migrar para o novo caminho.

Exemplo:
```
GET /api/catalogo/admin/produtos/644446611/complementos?apenas_ativos=false
Authorization: Bearer <TOKEN_ADMIN>
```

Resposta: lista de `ComplementoResponse` (mesmo formato antigo).

## Exemplo (curl)
```bash
curl -X PUT "https://seu-servidor/api/catalogo/admin/produtos/644446611" \
  -H "Authorization: Bearer <TOKEN_ADMIN>" \
  -F "cod_empresa=2" \
  -F "descricao=Nova descrição" \
  -F 'complementos={"configuracoes":[{"complemento_id":1,"ordem":0,"obrigatorio":false,"quantitativo":true,"minimo_itens":null,"maximo_itens":5}] }'
```

## Logs e verificação
- O servidor registra operações principais de CRUD. Logs detalhados de payloads não são emitidos por padrão — habilite logs de debug se precisar inspecionar payloads transmitidos.

Para verificar que a vinculação foi aplicada:
- Após o PUT de atualização com `complementos`, consulte:
  - GET /api/catalogo/admin/produtos/{cod_barras}/complementos?apenas_ativos=false
  - ou a listagem global: GET /api/catalogo/admin/complementos/?empresa_id={empresa_id}&apenas_ativos=false


## Migração
- Se você usa ainda o endpoint antigo `/api/catalogo/admin/complementos/produto/{cod_barras}/vincular`, atualize para o PUT no produto.  
- Posso adicionar um retorno 410 no endpoint antigo para facilitar a migração se preferir.

---
Documento gerado automaticamente pelo processo de unificação de endpoints.

