# Módulo de Mesas

Este módulo implementa o controle de mesas para o sistema, seguindo o padrão estabelecido no módulo delivery.

## Estrutura

```
app/api/mesas/
├── models/
│   ├── __init__.py
│   ├── model_mesa.py              # Modelo da tabela mesa
│   └── create_mesa_table.py       # Script para criar a tabela
├── schemas/
│   ├── __init__.py
│   └── schema_mesa.py             # Schemas Pydantic para validação
├── repositories/
│   ├── __init__.py
│   └── repo_mesas.py              # Camada de acesso aos dados
├── services/
│   ├── __init__.py
│   └── service_mesas.py           # Lógica de negócio
└── router/
    ├── __init__.py
    ├── router.py                  # Router principal
    ├── admin/
    │   ├── __init__.py
    │   └── router_mesas_admin.py  # Rotas para administradores
    └── client/
        ├── __init__.py
        └── router_mesas_client.py # Rotas para clientes
```

## Status das Mesas

- **D** - Disponível: Mesa livre para ocupação
- **O** - Ocupada: Mesa em uso
- **L** - Livre: Mesa liberada após uso
- **R** - Reservada: Mesa reservada para uso futuro

## Endpoints Disponíveis

### Admin (Autenticação: get_current_user)

#### Estatísticas
- `GET /api/mesas/admin/mesas/stats` - Estatísticas das mesas

#### Busca e Listagem
- `GET /api/mesas/admin/mesas/search` - Busca mesas com filtros
- `GET /api/mesas/admin/mesas` - Lista todas as mesas
- `GET /api/mesas/admin/mesas/{mesa_id}` - Busca mesa por ID

#### CRUD
- `POST /api/mesas/admin/mesas` - Cria nova mesa
- `PUT /api/mesas/admin/mesas/{mesa_id}` - Atualiza mesa
- `DELETE /api/mesas/admin/mesas/{mesa_id}` - Deleta mesa

#### Operações de Status
- `PATCH /api/mesas/admin/mesas/{mesa_id}/status` - Atualiza status
- `POST /api/mesas/admin/mesas/{mesa_id}/ocupar` - Ocupa mesa
- `POST /api/mesas/admin/mesas/{mesa_id}/liberar` - Libera mesa
- `POST /api/mesas/admin/mesas/{mesa_id}/reservar` - Reserva mesa
- `POST /api/mesas/admin/mesas/{mesa_id}/marcar-livre` - Marca como livre

### Cliente (Autenticação: get_current_client)

#### Consultas
- `GET /api/mesas/client/mesas/stats` - Estatísticas das mesas
- `GET /api/mesas/client/mesas` - Lista mesas ativas
- `GET /api/mesas/client/mesas/{mesa_id}` - Busca mesa por ID
- `GET /api/mesas/client/mesas/numero/{numero}` - Busca mesa por número

#### Filtros por Status
- `GET /api/mesas/client/mesas/disponiveis` - Mesas disponíveis
- `GET /api/mesas/client/mesas/ocupadas` - Mesas ocupadas
- `GET /api/mesas/client/mesas/reservadas` - Mesas reservadas
- `GET /api/mesas/client/mesas/livres` - Mesas livres

#### Utilitários
- `GET /api/mesas/client/mesas/{mesa_id}/disponivel` - Verifica disponibilidade
- `GET /api/mesas/client/mesas/capacidade/{capacidade_minima}` - Mesas por capacidade

## Modelo de Dados

### Tabela: mesas.mesa

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | SERIAL | Chave primária |
| numero | VARCHAR(10) | Número da mesa (único) |
| descricao | VARCHAR(100) | Descrição opcional |
| capacidade | INTEGER | Capacidade da mesa (padrão: 4) |
| status | VARCHAR(1) | Status: D, O, L, R |
| posicao_x | INTEGER | Posição X no layout |
| posicao_y | INTEGER | Posição Y no layout |
| ativa | VARCHAR(1) | Ativa: S, N |
| created_at | TIMESTAMP | Data de criação |
| updated_at | TIMESTAMP | Data de atualização |

## Uso

### Criar uma mesa

```python
from app.api.mesas.schemas.schema_mesa import MesaIn

mesa_data = MesaIn(
    numero="M01",
    descricao="Mesa próxima à janela",
    capacidade=4,
    posicao_x=100,
    posicao_y=200
)

service = MesaService(db)
mesa = service.create(mesa_data)
```

### Atualizar status

```python
from app.api.mesas.schemas.schema_mesa import StatusMesaEnum

# Ocupar mesa
service.ocupar_mesa(mesa_id)

# Liberar mesa
service.liberar_mesa(mesa_id)

# Reservar mesa
service.reservar_mesa(mesa_id)
```

## Validações

- Número da mesa deve ser único
- Capacidade deve estar entre 1 e 20
- Status deve ser um dos valores válidos (D, O, L, R)
- Mesa deve estar ativa para operações de status
- Não é possível deletar mesa com pedidos associados

## Logs

O módulo utiliza o sistema de logs centralizado da aplicação, registrando todas as operações importantes para auditoria e debugging.
