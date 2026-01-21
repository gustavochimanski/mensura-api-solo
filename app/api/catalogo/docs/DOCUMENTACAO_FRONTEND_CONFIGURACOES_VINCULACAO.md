# Documentação Frontend - Configurações de Complemento na Vinculação

## 📋 Visão Geral

A partir desta atualização, as configurações `obrigatorio`, `minimo_itens` e `maximo_itens` são definidas **na vinculação** entre complemento e item/receita/combo, e não mais no CRUD do complemento.

Isso permite que o mesmo complemento tenha comportamentos diferentes dependendo de onde está sendo usado.

## 🔄 Mudanças Principais

### Antes
- As configurações eram definidas no CRUD do complemento
- Todos os produtos/receitas/combos que usavam o mesmo complemento tinham as mesmas regras

### Agora
- As configurações são definidas ao vincular o complemento a um produto/receita/combo
- Cada vinculação pode ter suas próprias regras
- O mesmo complemento pode ser obrigatório em um produto e opcional em outro

## 📡 Endpoints Afetados

### 1. Vincular Complementos a Produto

**Endpoint:** `POST /api/catalogo/admin/produtos/{cod_barras}/complementos`

#### Formato Simples (Compatibilidade)
```json
{
  "complemento_ids": [1, 2, 3],
  "ordens": [0, 1, 2]
}
```

#### Formato Completo (Novo - Recomendado)
```json
{
  "configuracoes": [
    {
      "complemento_id": 1,
      "ordem": 0,
      "obrigatorio": true,
      "minimo_itens": 1,
      "maximo_itens": 3
    },
    {
      "complemento_id": 2,
      "ordem": 1,
      "obrigatorio": false,
      "minimo_itens": null,
      "maximo_itens": null
    },
    {
      "complemento_id": 3,
      "ordem": 2,
      "obrigatorio": true,
      "minimo_itens": 2,
      "maximo_itens": 5
    }
  ]
}
```

**Campos:**
- `complemento_id` (obrigatório): ID do complemento a vincular
- `ordem` (opcional): Ordem de exibição. Se não informado, usa o índice
- `obrigatorio` (opcional): Se o complemento é obrigatório nesta vinculação. Se `null`, usa o valor padrão do complemento
- `minimo_itens` (opcional): Quantidade mínima de itens. Se `null`, usa o valor padrão do complemento
- `maximo_itens` (opcional): Quantidade máxima de itens. Se `null`, usa o valor padrão do complemento

### 2. Vincular Complementos a Receita

**Endpoint:** `POST /api/catalogo/admin/receitas/{receita_id}/complementos`

Mesma estrutura do endpoint de produtos.

### 3. Vincular Complementos a Combo

**Endpoint:** `POST /api/catalogo/admin/combos/{combo_id}/complementos`

Mesma estrutura do endpoint de produtos.

## 📥 Responses

### Listar Complementos de um Produto/Receita/Combo

**Endpoint:** `GET /api/catalogo/admin/produtos/{cod_barras}/complementos`  
**Endpoint:** `GET /api/catalogo/public/complementos?tipo=produto&identificador={cod_barras}&tipo_pedido=delivery`

**Response:**
```json
{
  "id": 1,
  "nome": "Bebidas",
  "descricao": "Escolha sua bebida",
  "obrigatorio": true,        // ← Da vinculação
  "quantitativo": false,      // ← Do complemento (não muda)
  "minimo_itens": 1,          // ← Da vinculação
  "maximo_itens": 3,          // ← Da vinculação
  "ordem": 0,                 // ← Da vinculação
  "ativo": true,
  "adicionais": [...]
}
```

**Importante:** Os campos `obrigatorio`, `minimo_itens`, `maximo_itens` e `ordem` agora vêm da **vinculação**, não mais do complemento em si.

## 🎯 Exemplos de Uso

### Exemplo 1: Complemento Obrigatório em um Produto, Opcional em Outro

```javascript
// Produto 1: Bebida obrigatória
await vincularComplementosProduto('PROD001', {
  configuracoes: [
    {
      complemento_id: 1, // Bebidas
      ordem: 0,
      obrigatorio: true,
      minimo_itens: 1,
      maximo_itens: 1
    }
  ]
});

// Produto 2: Bebida opcional
await vincularComplementosProduto('PROD002', {
  configuracoes: [
    {
      complemento_id: 1, // Mesmo complemento de bebidas
      ordem: 0,
      obrigatorio: false,  // ← Diferente!
      minimo_itens: null,
      maximo_itens: null
    }
  ]
});
```

### Exemplo 2: Diferentes Limites por Produto

```javascript
// Hambúrguer simples: até 3 adicionais
await vincularComplementosProduto('HAMB001', {
  configuracoes: [
    {
      complemento_id: 2, // Adicionais
      ordem: 0,
      obrigatorio: false,
      minimo_itens: 0,
      maximo_itens: 3  // ← Limite de 3
    }
  ]
});

// Hambúrguer especial: até 5 adicionais
await vincularComplementosProduto('HAMB002', {
  configuracoes: [
    {
      complemento_id: 2, // Mesmo complemento de adicionais
      ordem: 0,
      obrigatorio: false,
      minimo_itens: 0,
      maximo_itens: 5  // ← Limite de 5
    }
  ]
});
```

## 🔧 Migração do Frontend

### Passo 1: Atualizar Formulários de Vinculação

Se você tinha um formulário simples que apenas selecionava complementos:

**Antes:**
```javascript
const vincularComplementos = async (itemId, complementoIds) => {
  await api.post(`/produtos/${itemId}/complementos`, {
    complemento_ids: complementoIds,
    ordens: complementoIds.map((_, idx) => idx)
  });
};
```

**Depois:**
```javascript
const vincularComplementos = async (itemId, configuracoes) => {
  await api.post(`/produtos/${itemId}/complementos`, {
    configuracoes: configuracoes.map((cfg, idx) => ({
      complemento_id: cfg.id,
      ordem: cfg.ordem ?? idx,
      obrigatorio: cfg.obrigatorio ?? null,
      minimo_itens: cfg.minimo_itens ?? null,
      maximo_itens: cfg.maximo_itens ?? null
    }))
  });
};
```

### Passo 2: Atualizar Exibição de Complementos

Ao exibir complementos de um produto/receita/combo, use os valores retornados diretamente:

```javascript
// Os valores já vêm corretos da API
complementos.forEach(complemento => {
  if (complemento.obrigatorio) {
    // Exibir como obrigatório
  }
  
  if (complemento.minimo_itens > 0) {
    // Exibir mensagem de mínimo
  }
  
  if (complemento.maximo_itens) {
    // Exibir mensagem de máximo
  }
});
```

### Passo 3: Validação no Frontend

Use os valores retornados pela API para validação:

```javascript
const validarComplementos = (complementos, selecoes) => {
  const erros = [];
  
  complementos.forEach(complemento => {
    const selecionados = selecoes.filter(s => s.complemento_id === complemento.id);
    const qtdSelecionada = selecionados.reduce((sum, s) => sum + s.quantidade, 0);
    
    // Valida obrigatório
    if (complemento.obrigatorio && qtdSelecionada === 0) {
      erros.push(`${complemento.nome} é obrigatório`);
    }
    
    // Valida mínimo
    if (complemento.minimo_itens && qtdSelecionada < complemento.minimo_itens) {
      erros.push(`${complemento.nome}: escolha pelo menos ${complemento.minimo_itens} item(ns)`);
    }
    
    // Valida máximo
    if (complemento.maximo_itens && qtdSelecionada > complemento.maximo_itens) {
      erros.push(`${complemento.nome}: escolha no máximo ${complemento.maximo_itens} item(ns)`);
    }
  });
  
  return erros;
};
```

## ⚠️ Compatibilidade

O formato simples (`complemento_ids` + `ordens`) ainda é suportado para manter compatibilidade com código legado. No entanto, **recomendamos migrar para o formato completo** (`configuracoes`) para ter controle total sobre as configurações.

Quando usar o formato simples, os valores padrão do complemento serão usados.

## 📝 Notas Importantes

1. **Campo `quantitativo`**: Este campo continua vindo do complemento e não muda por vinculação. Ele indica se o complemento permite quantidades (ex: "2x bacon").

2. **Valores `null`**: Quando `obrigatorio`, `minimo_itens` ou `maximo_itens` são `null` na vinculação, os valores padrão do complemento são usados.

3. **Ordem**: A ordem também vem da vinculação, permitindo ordenar complementos de forma diferente em cada produto/receita/combo.

4. **CRUD do Complemento**: O CRUD do complemento ainda existe, mas as configurações lá são apenas valores padrão. As configurações reais vêm da vinculação.

## 🐛 Troubleshooting

### Problema: Complementos não aparecem com as configurações corretas

**Solução:** Verifique se você está usando o endpoint correto para listar complementos. Use:
- `GET /api/catalogo/admin/produtos/{cod_barras}/complementos` (admin)
- `GET /api/catalogo/public/complementos?tipo=produto&identificador={cod_barras}&tipo_pedido=delivery` (público)

Não use o endpoint genérico de complementos (`GET /api/catalogo/admin/complementos/`), pois ele retorna os valores padrão do complemento, não da vinculação.

### Problema: Validações não funcionam

**Solução:** Certifique-se de usar os valores retornados pela API (`obrigatorio`, `minimo_itens`, `maximo_itens` da resposta), não os valores do complemento em si.

## 📞 Suporte

Em caso de dúvidas, consulte a documentação da API ou entre em contato com a equipe de backend.
