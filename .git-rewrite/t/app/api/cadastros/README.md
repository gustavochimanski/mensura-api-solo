# Schema de Cadastros

Este módulo centraliza todos os schemas relacionados a CRUD de entidades de cadastro do sistema.

## Estrutura

```
app/api/cadastros/
├── __init__.py
├── schemas/
│   ├── __init__.py
│   ├── schema_produtos.py
│   ├── schema_adicional.py
│   ├── schema_cliente.py
│   ├── schema_combo.py
│   ├── schema_meio_pagamento.py
│   ├── schema_categoria.py
│   ├── schema_cupom.py
│   ├── schema_vitrine.py
│   └── schema_parceiros.py
└── README.md
```

## Schemas Disponíveis

### Produtos (`schema_produtos.py`)
- `CriarNovoProdutoRequest`
- `AtualizarProdutoRequest`
- `ProdutoBaseDTO`
- `ProdutoEmpDTO`
- `CriarNovoProdutoResponse`
- `ProdutoListItem`
- `ProdutosPaginadosResponse`

### Adicionais (`schema_adicional.py`)
- `CriarAdicionalRequest`
- `AtualizarAdicionalRequest`
- `AdicionalResponse`
- `AdicionalResumidoResponse`
- `VincularAdicionaisProdutoRequest`
- `VincularAdicionaisProdutoResponse`

### Clientes (`schema_cliente.py`)
- `ClienteOut`
- `ClienteCreate`
- `ClienteUpdate`
- `ClienteAdminUpdate`
- `EnderecoUpdateAdmin`
- `NovoDispositivoRequest`

### Combos (`schema_combo.py`)
- `ComboItemIn`
- `CriarComboRequest`
- `AtualizarComboRequest`
- `ComboItemDTO`
- `ComboDTO`
- `ListaCombosResponse`

### Meios de Pagamento (`schema_meio_pagamento.py`)
- `MeioPagamentoTipoEnum`
- `MeioPagamentoBase`
- `MeioPagamentoCreate`
- `MeioPagamentoUpdate`
- `MeioPagamentoResponse`

### Categorias (`schema_categoria.py`)
- `CategoriaDeliveryIn`
- `CategoriaDeliveryOut`
- `CategoriaSearchOut`
- `CategoriaFlatOut`

### Cupons (`schema_cupom.py`)
- `CupomCreate`
- `CupomUpdate`
- `CupomOut`
- `CupomParceiroOut`

### Vitrines (`schema_vitrine.py`)
- `CriarVitrineRequest`
- `AtualizarVitrineRequest`
- `VitrineOut`

### Parceiros (`schema_parceiros.py`)
- `BannerParceiroIn`
- `BannerParceiroOut`
- `ParceiroIn`
- `ParceiroOut`
- `ParceiroCompletoOut`

## Uso

Para usar os schemas, você pode importá-los diretamente do módulo `cadastros.schemas`:

```python
from app.api.cadastros.schemas import (
    CriarNovoProdutoRequest,
    ProdutoBaseDTO,
    CriarAdicionalRequest,
    ClienteCreate,
    # ... outros schemas
)
```

Ou importar de módulos específicos:

```python
from app.api.catalogo.schemas.schema_produtos import CriarNovoProdutoRequest
from app.api.catalogo.schemas.schema_adicional import CriarAdicionalRequest
```

## Migração

Os schemas antigos ainda existem nos módulos originais (`delivery` e `mensura`), mas agora todos os novos CRUDs de cadastros devem usar este schema centralizado.

## Notas

- Todos os schemas usam `ConfigDict(from_attributes=True)` para compatibilidade com SQLAlchemy
- Schemas que dependem de outros (como `ParceiroCompletoOut` usando `CupomParceiroOut`) usam forward references para evitar dependências circulares
