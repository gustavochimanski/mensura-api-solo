# Schemas da API de Mesas - Referência Técnica

## Schemas de Request (Pydantic)

### 1. MesaCreate

```python
class MesaCreate(BaseModel):
    codigo: Decimal = Field(..., gt=0)           # Código da mesa (> 0)
    descricao: str = Field(..., min_length=1)    # Descrição (não vazio)
    capacidade: int = Field(..., gt=0)           # Capacidade máxima (> 0)
    status: str = Field(...)                     # "D", "O" ou "R"
    ativa: str = Field(...)                      # "S" ou "N"
    empresa_id: int = Field(..., gt=0)           # ID da empresa (> 0)
```

**Validações:**
- `status`: Deve ser "D", "O" ou "R"
- `ativa`: Deve ser "S" ou "N"

**Exemplo JSON:**
```json
{
  "codigo": 1,
  "descricao": "Mesa 1",
  "capacidade": 4,
  "status": "D",
  "ativa": "S",
  "empresa_id": 1
}
```

---

### 2. MesaUpdate

```python
class MesaUpdate(BaseModel):
    descricao: Optional[str] = Field(None, min_length=1)
    capacidade: Optional[int] = Field(None, gt=0)
    status: Optional[str] = None
    ativa: Optional[str] = None
    empresa_id: Optional[int] = Field(None, gt=0)
```

**Validações:**
- Todos os campos são opcionais
- Se `status` for fornecido, deve ser "D", "O" ou "R"
- Se `ativa` for fornecida, deve ser "S" ou "N"

**Exemplo JSON:**
```json
{
  "descricao": "Mesa 1 - Atualizada",
  "capacidade": 6,
  "status": "O"
}
```

---

### 3. MesaStatusUpdate

```python
class MesaStatusUpdate(BaseModel):
    status: str = Field(...)  # "D", "O" ou "R"
```

**Validações:**
- `status`: Deve ser "D", "O" ou "R"

**Exemplo JSON:**
```json
{
  "status": "O"
}
```

---

## Schemas de Response (Pydantic)

### 1. PedidoAbertoMesa

```python
class PedidoAbertoMesa(BaseModel):
    id: int
    numero_pedido: str
    status: str
    num_pessoas: Optional[int] = None
    valor_total: Decimal
    cliente_id: Optional[int] = None
    cliente_nome: Optional[str] = None
```

**Exemplo JSON:**
```json
{
  "id": 123,
  "numero_pedido": "PED-001",
  "status": "A",
  "num_pessoas": 2,
  "valor_total": 45.50,
  "cliente_id": 10,
  "cliente_nome": "João Silva"
}
```

---

### 2. MesaResponse

```python
class MesaResponse(BaseModel):
    id: int
    codigo: str                                 # Convertido de Decimal para string
    numero: str
    descricao: Optional[str]
    capacidade: int
    status: str                                 # "D", "O" ou "R"
    status_descricao: str                       # Ex: "Disponível"
    ativa: str                                  # "S" ou "N"
    label: str                                  # Ex: "Mesa 1"
    num_pessoas_atual: Optional[int] = None
    empresa_id: Optional[int] = None
    pedidos_abertos: Optional[List[PedidoAbertoMesa]] = None
```

**Exemplo JSON:**
```json
{
  "id": 1,
  "codigo": "1",
  "numero": "1",
  "descricao": "Mesa 1",
  "capacidade": 4,
  "status": "D",
  "status_descricao": "Disponível",
  "ativa": "S",
  "label": "Mesa 1",
  "num_pessoas_atual": 2,
  "empresa_id": 1,
  "pedidos_abertos": [
    {
      "id": 123,
      "numero_pedido": "PED-001",
      "status": "A",
      "num_pessoas": 2,
      "valor_total": 45.50,
      "cliente_id": 10,
      "cliente_nome": "João Silva"
    }
  ]
}
```

---

### 3. MesaStatsResponse

```python
class MesaStatsResponse(BaseModel):
    total: int
    disponiveis: int
    ocupadas: int
    reservadas: int
    inativas: int
```

**Exemplo JSON:**
```json
{
  "total": 20,
  "disponiveis": 12,
  "ocupadas": 5,
  "reservadas": 2,
  "inativas": 1
}
```

---

## Modelo do Banco de Dados

### MesaModel

```python
class MesaModel(Base):
    __tablename__ = "mesas"
    __table_args__ = {"schema": "cadastros"}
    
    id: int                                     # PK
    codigo: Decimal(10, 2)                     # Código único por empresa
    numero: str(10)                            # Número único por empresa
    descricao: str(100)                        # Descrição opcional
    capacidade: int                            # Capacidade máxima
    status: StatusMesaType                     # "D", "O" ou "R"
    ativa: str(1)                              # "S" ou "N"
    empresa_id: int                            # FK para empresas
    cliente_atual_id: Optional[int]            # FK para clientes
    created_at: DateTime
    updated_at: DateTime
```

**Constraints:**
- `uq_mesa_empresa_codigo`: (empresa_id, codigo) único
- `uq_mesa_empresa_numero`: (empresa_id, numero) único
- `idx_mesa_empresa`: índice em empresa_id

---

## Enums

### StatusMesa

```python
class StatusMesa(str, enum.Enum):
    DISPONIVEL = "D"   # Disponível
    OCUPADA = "O"      # Ocupada
    RESERVADA = "R"    # Reservada
```

---

## Mapeamento de Dados

### Conversão de Modelo para Response

1. **codigo**: `Decimal` → `str`
2. **status**: `StatusMesa` enum → `str` (value)
3. **status_descricao**: Calculado via property do modelo
4. **label**: Calculado via property do modelo
5. **num_pessoas_atual**: Calculado somando `num_pessoas` dos pedidos abertos
6. **pedidos_abertos**: Buscado via repositório de pedidos

### Pedidos Abertos

Os pedidos abertos são buscados de duas fontes:

1. **Pedidos de Mesa** (`tipo_entrega = MESA`):
   - Incluem `num_pessoas`
   - Contribuem para `num_pessoas_atual`

2. **Pedidos de Balcão** (`tipo_entrega = BALCAO`):
   - Não incluem `num_pessoas`
   - Não contribuem para `num_pessoas_atual`

**Status Considerados Abertos:**
- P (Pendente)
- I (Impressão)
- R (Preparando)
- A (Aguardando pagamento)
- Outros status que não sejam "E" (Entregue) ou "C" (Cancelado)

---

## Validações de Negócio

### Criação de Mesa

1. Verifica se já existe mesa com o mesmo `codigo` na empresa
2. Verifica se já existe mesa com o mesmo `numero` na empresa
3. Gera `numero` automaticamente a partir do `codigo`
4. Valida que `empresa_id` do body corresponde ao da query

### Atualização de Mesa

1. Verifica se a mesa existe
2. Verifica se a mesa pertence à empresa
3. Valida que não é possível alterar a empresa da mesa
4. Atualiza apenas campos fornecidos (PATCH-like)

### Operações de Status

1. **Ocupar**: Muda status para "O"
2. **Liberar**: Muda status para "D" e limpa `cliente_atual_id`
3. **Reservar**: Muda status para "R"
4. **Atualizar Status**: Permite definir qualquer status válido

---

## Tratamento de Erros

### Códigos HTTP

- **200**: Sucesso (GET, PUT, PATCH, DELETE)
- **201**: Criado (POST)
- **400**: Erro de validação ou requisição inválida
- **403**: Mesa não pertence à empresa
- **404**: Mesa não encontrada
- **422**: Erro de validação de dados

### Formato de Erro

```json
{
  "detail": "Mensagem de erro descritiva"
}
```

**Exemplos:**
- `"Mesa não encontrada"`
- `"Mesa não pertence à empresa informada"`
- `"Já existe uma mesa com código 1 nesta empresa"`
- `"Status deve ser 'D', 'O' ou 'R'"`

---

## Estrutura de Arquivos

```
app/api/cadastros/
├── models/
│   └── model_mesa.py                    # Modelo SQLAlchemy
├── repositories/
│   └── repo_mesas.py                    # Repository (CRUD + operações)
├── services/
│   └── service_mesas.py                 # Service (lógica de negócio)
├── schemas/
│   └── schema_mesa.py                   # Schemas Pydantic
└── router/
    └── admin/
        └── router_mesas.py              # Router FastAPI
```

---

## Dependências

### Imports Principais

**Router:**
- `fastapi`: APIRouter, Depends, Query, HTTPException, status
- `sqlalchemy.orm`: Session
- `app.core.admin_dependencies`: get_current_user
- `app.database.db_connection`: get_db

**Service:**
- `sqlalchemy.orm`: Session
- `fastapi`: HTTPException
- `app.api.pedidos.repositories.repo_pedidos`: PedidoRepository
- `app.api.pedidos.models.model_pedido_unificado`: TipoEntrega

**Repository:**
- `sqlalchemy.orm`: Session
- `sqlalchemy`: and_, or_, func
- `app.api.cadastros.models.model_mesa`: MesaModel, StatusMesa

---

## Integrações

### Com API de Pedidos

A API de mesas se integra com a API de pedidos através de:

1. **PedidoRepository.list_abertos_by_mesa()**
   - Busca pedidos de mesa abertos
   - Busca pedidos de balcão abertos
   - Filtra por `mesa_id` e status aberto

2. **Cálculo de num_pessoas_atual**
   - Soma `num_pessoas` dos pedidos de mesa abertos
   - Ignora pedidos de balcão (não têm `num_pessoas`)

3. **Inclusão de Pedidos Abertos na Resposta**
   - Combina pedidos de mesa e balcão
   - Formata para schema `PedidoAbertoMesa`

---

## Performance e Otimizações

### Eager Loading

O serviço utiliza `joinedload` para evitar N+1 queries:

- Pedidos com itens carregados
- Cliente associado aos pedidos
- Mesa relacionada

### Índices do Banco

- `idx_mesa_empresa`: Acelera filtros por empresa
- `idx_pedidos_empresa_tipo_status`: Acelera buscas de pedidos abertos
- `uq_mesa_empresa_codigo`: Garante unicidade
- `uq_mesa_empresa_numero`: Garante unicidade

---

## Testes Recomendados

### Casos de Teste

1. **Criação**
   - Criar mesa válida
   - Tentar criar com código duplicado
   - Tentar criar com empresa_id inválido

2. **Listagem**
   - Listar todas as mesas
   - Filtrar por status
   - Filtrar por ativa

3. **Busca**
   - Buscar por número
   - Buscar por descrição
   - Buscar com múltiplos filtros

4. **Atualização**
   - Atualizar campos individuais
   - Atualizar status
   - Tentar atualizar mesa de outra empresa

5. **Operações de Status**
   - Ocupar mesa
   - Liberar mesa
   - Reservar mesa

6. **Estatísticas**
   - Verificar contagens corretas
   - Testar com mesas vazias

7. **Pedidos Abertos**
   - Mesa sem pedidos
   - Mesa com pedidos de mesa
   - Mesa com pedidos de balcão
   - Mesa com ambos os tipos

---

## Notas de Implementação

1. **Número da Mesa**: Gerado automaticamente a partir do `codigo` na criação
2. **Pedidos Abertos**: Busca inclui pedidos de mesa E balcão associados
3. **num_pessoas_atual**: Calculado apenas a partir de pedidos de mesa
4. **Status**: Usa enum `StatusMesa` internamente, retorna string na API
5. **Validações**: Realizadas tanto no schema Pydantic quanto no service

