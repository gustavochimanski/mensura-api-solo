# ProductCore - Sistema Unificado de Produtos

O `ProductCore` é um sistema unificado para lidar com diferentes tipos de produtos (produtos simples, combos, receitas) de forma consistente, abstraindo as diferenças entre eles.

## 🎯 Objetivo

Simplificar o tratamento de produtos, combos, receitas, complementos e adicionais através de uma interface única, eliminando a necessidade de código duplicado e lógica condicional espalhada.

## 📦 Componentes

### ProductType (Enum)
Enum para identificar o tipo de produto:
- `PRODUTO`: Produto simples
- `COMBO`: Combo de produtos
- `RECEITA`: Receita

### ProductBase (Dataclass)
Classe base unificada que representa qualquer tipo de produto:
- `product_type`: Tipo do produto
- `identifier`: Identificador (cod_barras para produtos, id para combos/receitas)
- `empresa_id`: ID da empresa
- `nome`: Nome do produto
- `preco_base`: Preço base
- `ativo`: Se está ativo
- `disponivel`: Se está disponível

### ProductCore (Classe Principal)
Classe principal que fornece métodos unificados para trabalhar com produtos.

## 🚀 Uso Básico

### Inicialização

```python
from app.api.catalogo.core import ProductCore
from app.api.catalogo.adapters.produto_adapter import ProdutoAdapter
from app.api.catalogo.adapters.combo_adapter import ComboAdapter
from app.api.catalogo.adapters.complemento_adapter import ComplementoAdapter

# Criar adapters (ou usar os existentes)
produto_adapter = ProdutoAdapter(db)
combo_adapter = ComboAdapter(db)
complemento_adapter = ComplementoAdapter(db)

# Criar ProductCore
product_core = ProductCore(
    produto_contract=produto_adapter,
    combo_contract=combo_adapter,
    complemento_contract=complemento_adapter,
)
```

### Buscar Produtos

```python
# Buscar produto por código de barras
produto = product_core.buscar_produto(empresa_id=1, cod_barras="PROD001")

# Buscar combo por ID
combo = product_core.buscar_combo(combo_id=5)

# Buscar qualquer tipo
item = product_core.buscar_qualquer(
    empresa_id=1,
    cod_barras="PROD001",  # ou combo_id=5, ou receita_id=3
)
```

### Validar Disponibilidade

```python
# Validar se produto está disponível
if product_core.validar_disponivel(produto, quantidade=2):
    print("Produto disponível!")
    
# Validar se pertence à empresa
if product_core.validar_empresa(produto, empresa_id=1):
    print("Produto pertence à empresa!")
```

### Calcular Preços com Complementos

```python
from app.api.pedidos.schemas.schema_pedido import ComplementoRequest

# Definir complementos selecionados
complementos = [
    ComplementoRequest(
        complemento_id=1,
        adicionais=[
            AdicionalRequest(adicional_id=10, quantidade=2),
            AdicionalRequest(adicional_id=11, quantidade=1),
        ]
    )
]

# Calcular preço total
preco_total, snapshot = product_core.calcular_preco_com_complementos(
    product=produto,
    quantidade=2,
    complementos_request=complementos,
)

print(f"Preço total: R$ {preco_total}")
print(f"Snapshot: {snapshot}")
```

### Listar Complementos

```python
# Listar todos os complementos de um produto
complementos = product_core.listar_complementos(produto, apenas_ativos=True)

for complemento in complementos:
    print(f"Complemento: {complemento.nome}")
    for adicional in complemento.adicionais:
        print(f"  - {adicional.nome}: R$ {adicional.preco}")
```

## 📝 Exemplo Completo: Processar Item de Pedido

```python
def processar_item_pedido(
    product_core: ProductCore,
    empresa_id: int,
    cod_barras: str = None,
    combo_id: int = None,
    receita_id: int = None,
    quantidade: int = 1,
    complementos: List = None,
):
    # Buscar produto
    produto = product_core.buscar_qualquer(
        empresa_id=empresa_id,
        cod_barras=cod_barras,
        combo_id=combo_id,
        receita_id=receita_id,
    )
    
    if not produto:
        raise ValueError("Produto não encontrado")
    
    # Validar disponibilidade
    if not product_core.validar_disponivel(produto, quantidade):
        raise ValueError("Produto não disponível")
    
    # Validar empresa
    if not product_core.validar_empresa(produto, empresa_id):
        raise ValueError("Produto não pertence à empresa")
    
    # Calcular preço com complementos
    preco_total, snapshot = product_core.calcular_preco_com_complementos(
        product=produto,
        quantidade=quantidade,
        complementos_request=complementos,
    )
    
    return {
        "produto": produto,
        "preco_total": preco_total,
        "complementos_snapshot": snapshot,
    }
```

## 🔧 Métodos Disponíveis

### Busca
- `buscar_produto(empresa_id, cod_barras)`: Busca produto por código de barras
- `buscar_combo(combo_id)`: Busca combo por ID
- `buscar_receita(receita_id, empresa_id, receita_model)`: Busca receita por ID
- `buscar_qualquer(...)`: Busca qualquer tipo de produto
- `criar_de_modelo(model)`: Cria ProductBase a partir de modelo SQLAlchemy

### Validação
- `validar_disponivel(product, quantidade)`: Valida disponibilidade
- `validar_empresa(product, empresa_id)`: Valida se pertence à empresa

### Complementos
- `listar_complementos(product, apenas_ativos)`: Lista complementos do produto
- `calcular_preco_com_complementos(product, quantidade, complementos_request)`: Calcula preço total

### Utilitários
- `obter_descricao_completa(product)`: Obtém descrição formatada
- `obter_identificador_formatado(product)`: Obtém identificador formatado

## 💡 Vantagens

1. **Código Unificado**: Uma única interface para todos os tipos de produtos
2. **Menos Duplicação**: Elimina código repetido entre produtos, combos e receitas
3. **Fácil Manutenção**: Mudanças em um lugar afetam todos os tipos
4. **Type Safety**: Uso de enums e dataclasses para type safety
5. **Flexibilidade**: Pode ser usado com ou sem contracts/adapters

## 🔄 Migração

Para migrar código existente:

**Antes:**
```python
if cod_barras:
    produto = produto_contract.obter_produto_emp_por_cod(empresa_id, cod_barras)
    preco = produto.preco_venda
elif combo_id:
    combo = combo_contract.buscar_por_id(combo_id)
    preco = combo.preco_total
# ... código duplicado para cada tipo
```

**Depois:**
```python
product = product_core.buscar_qualquer(
    empresa_id=empresa_id,
    cod_barras=cod_barras,
    combo_id=combo_id,
)
preco = product.get_preco_venda()
```

## 🆕 Métodos Helper Avançados

### processar_item_pedido()

Processa um item completo de pedido em um único método:

```python
dados = product_core.processar_item_pedido(
    product=produto,
    quantidade=2,
    complementos_request=complementos,
    observacao="Sem cebola",
)

# Retorna:
# {
#     'product': ProductBase,
#     'preco_total': Decimal,
#     'preco_unitario': Decimal,
#     'complementos_snapshot': List[Dict],
#     'descricao': str,
#     'observacao_formatada': str,
#     'tipo': str,
# }
```

### validar_e_processar_item()

Método completo que busca, valida e processa em uma única chamada:

```python
try:
    dados = product_core.validar_e_processar_item(
        empresa_id=1,
        cod_barras="PROD001",
        quantidade=2,
        complementos_request=complementos,
        observacao="Sem cebola",
    )
    # Usa dados['preco_total'], dados['complementos_snapshot'], etc.
except ValueError as e:
    # Trata erros de validação
    print(f"Erro: {e}")
```

## 📚 Ver Também

- `app/api/catalogo/contracts/`: Contracts para acesso aos dados
- `app/api/catalogo/adapters/`: Adapters que implementam os contracts
- `app/api/pedidos/utils/complementos.py`: Funções auxiliares para complementos
- `CHANGELOG.md`: Histórico de mudanças

