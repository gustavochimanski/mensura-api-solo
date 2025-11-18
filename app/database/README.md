# Sistema de Inicialização do Banco de Dados - Arquitetura DDD

## 📋 Visão Geral

Este módulo implementa uma arquitetura **Domain-Driven Design (DDD)** para a inicialização do banco de dados, separando responsabilidades por domínio e criando um sistema modular e extensível.

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    Database Orchestrator                      │
│              (Coordena toda a inicialização)                  │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
    ┌───────▼────────┐            ┌────────▼────────┐
    │ Infrastructure │            │ Domain Registry  │
    │   (Compartilhada)│            │  (Auto-registro) │
    └─────────────────┘            └──────────────────┘
            │                               │
    ┌───────┴───────┐              ┌────────┴────────┐
    │               │              │                  │
┌───▼───┐    ┌──────▼──────┐  ┌────▼────┐    ┌────────▼──────┐
│PostGIS│    │  Timezone   │  │Cadastros│    │   Cardápio    │
└───────┘    └─────────────┘  └─────────┘    └───────────────┘
┌───────┐    ┌─────────────┐  ┌────────┐    ┌───────────────┐
│Schemas│    │    ENUMs     │  │ Mesas  │    │    Balcão     │
└───────┘    └─────────────┘  └─────────┘    └───────────────┘
```

## 📁 Estrutura de Diretórios

```
app/database/
├── infrastructure/          # Infraestrutura compartilhada
│   ├── __init__.py
│   ├── postgis.py           # Configuração PostGIS
│   ├── timezone.py          # Configuração timezone
│   ├── schemas.py           # Criação de schemas
│   └── enums.py             # Criação de ENUMs
│
├── domain/                  # Sistema de domínios
│   ├── __init__.py
│   ├── base.py              # Classe base abstrata
│   ├── registry.py           # Registry de domínios
│   └── orchestrator.py      # Orquestrador principal
│
├── init_db.py               # Código legado (manter compatibilidade)
├── init_db_refactored.py    # Versão refatorada
│
├── DOMAIN_SYSTEM_DESIGN.md  # Documentação do design
├── EXEMPLO_USO.md           # Guia de uso
└── README.md                # Este arquivo

app/api/
├── cadastros/
│   └── database/
│       ├── __init__.py
│       └── initializer.py   # Inicializador do domínio
├── cardapio/
│   └── database/
│       ├── __init__.py
│       └── initializer.py
└── ... (outros domínios)
```

## 🔄 Fluxo de Inicialização

```
1. Importar inicializadores de domínios
   ↓ (auto-registro no registry)
2. Criar DatabaseOrchestrator
   ↓
3. Inicializar Infraestrutura
   ├── Configurar timezone
   ├── Habilitar PostGIS
   ├── Criar schemas
   └── Criar ENUMs
   ↓
4. Inicializar Domínios (na ordem de registro)
   ├── Cadastros
   │   ├── Criar tabelas
   │   └── Criar usuário admin
   ├── Cardápio
   │   └── Criar tabelas
   ├── Mesas
   │   └── Criar tabelas
   └── ... (outros domínios)
   ↓
5. Validação final
```

## 🎯 Componentes Principais

### 1. Infrastructure Module
Configurações globais do banco:
- **postgis.py**: Habilita extensão PostGIS
- **timezone.py**: Configura timezone
- **schemas.py**: Cria schemas do banco
- **enums.py**: Cria ENUMs compartilhados

### 2. Domain Base
Classe abstrata para inicializadores:
- `get_domain_name()`: Nome do domínio
- `get_schema_name()`: Schema do banco
- `initialize_tables()`: Cria tabelas
- `initialize_data()`: Popula dados iniciais
- `validate()`: Valida inicialização
- `initialize()`: Método principal

### 3. Domain Registry
Sistema de registro automático:
- Singleton pattern
- Auto-registro ao importar
- Descoberta de domínios

### 4. Database Orchestrator
Coordena a inicialização:
- Orquestra infraestrutura
- Orquestra domínios
- Trata erros
- Logging centralizado

## 💡 Como Usar

### Inicialização Simples

```python
from app.database.domain.orchestrator import inicializar_banco

inicializar_banco()
```

### Adicionar Novo Domínio

1. Criar `app/api/seu_dominio/database/initializer.py`
2. Implementar `DomainInitializer`
3. Registrar com `register_domain()`
4. Importar no ponto de entrada

Veja `EXEMPLO_USO.md` para detalhes.

## ✅ Benefícios

- **Modularidade**: Cada domínio é independente
- **Manutenibilidade**: Fácil localizar código
- **Extensibilidade**: Adicionar domínios é simples
- **Testabilidade**: Testar domínios isoladamente
- **Escalabilidade**: Suporta crescimento
- **Clareza**: Responsabilidades bem definidas

## 📚 Documentação

- **DOMAIN_SYSTEM_DESIGN.md**: Design completo da arquitetura
- **EXEMPLO_USO.md**: Guia prático de uso
- **README.md**: Este arquivo (visão geral)

## 🔧 Migração

O arquivo `init_db.py` atual será gradualmente migrado para usar este sistema. A versão refatorada está em `init_db_refactored.py` e mantém compatibilidade com o código existente.

## 🚀 Próximos Passos

1. ✅ Estrutura base criada
2. ✅ Exemplos de domínios implementados
3. ⏳ Migrar domínios restantes
4. ⏳ Adicionar testes unitários
5. ⏳ Documentar cada domínio específico

