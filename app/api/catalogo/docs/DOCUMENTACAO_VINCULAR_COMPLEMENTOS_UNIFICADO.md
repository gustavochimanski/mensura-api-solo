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

## Exemplo (curl)
```bash
curl -X PUT "https://seu-servidor/api/catalogo/admin/produtos/644446611" \
  -H "Authorization: Bearer <TOKEN_ADMIN>" \
  -F "cod_empresa=2" \
  -F "descricao=Nova descrição" \
  -F 'complementos={"configuracoes":[{"complemento_id":1,"ordem":0,"obrigatorio":false,"quantitativo":true,"minimo_itens":null,"maximo_itens":5}] }'
```

## Logs e verificação
- O servidor registra:
  - A string bruta enviada em `complementos` (`logger.info`).
  - O payload parseado (`logger.info`) antes da vinculação.
  - A resposta do serviço de vinculação (para verificar IDs vinculados).
  - Dentro do `ComplementoService.vincular_complementos_produto` também há log do payload recebido.

Use esses logs para confirmar que a configuração enviada está sendo aplicada.

## Migração
- Se você usa ainda o endpoint antigo `/api/catalogo/admin/complementos/produto/{cod_barras}/vincular`, atualize para o PUT no produto.  
- Posso adicionar um retorno 410 no endpoint antigo para facilitar a migração se preferir.

---
Documento gerado automaticamente pelo processo de unificação de endpoints.

