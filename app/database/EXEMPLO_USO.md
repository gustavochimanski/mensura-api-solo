# Exemplo de Uso - Sistema de Domínios

## Como Adicionar um Novo Domínio

### 1. Criar a estrutura de diretórios

```bash
app/api/seu_dominio/
└── database/
    ├── __init__.py
    └── initializer.py
```

### 2. Implementar o Inicializador

```python
# app/api/seu_dominio/database/initializer.py
import logging
from app.database.domain.base import DomainInitializer
from app.database.domain.registry import register_domain

# Importar seus models
from app.api.seu_dominio.models.model_exemplo import ExemploModel

logger = logging.getLogger(__name__)


class SeuDominioInitializer(DomainInitializer):
    """Inicializador do domínio SeuDominio."""
    
    def get_domain_name(self) -> str:
        return "seu_dominio"
    
    def get_schema_name(self) -> str:
        return "seu_dominio"  # ou outro schema se necessário
    
    def initialize_data(self) -> None:
        """Popula dados iniciais (opcional)."""
        # Exemplo: criar dados padrão
        pass
    
    def validate(self) -> bool:
        """Valida se a inicialização foi bem-sucedida (opcional)."""
        # Exemplo: verificar se tabelas foram criadas
        return True


# Cria e registra a instância
_seu_dominio_initializer = SeuDominioInitializer()
register_domain(_seu_dominio_initializer)
```

### 3. Exportar no __init__.py

```python
# app/api/seu_dominio/database/__init__.py
from .initializer import SeuDominioInitializer

__all__ = ["SeuDominioInitializer"]
```

### 4. Importar no ponto de entrada

```python
# app/database/init_db_refactored.py
from app.api.seu_dominio.database import SeuDominioInitializer  # noqa: F401
```

## Como Usar o Sistema

### Inicialização Básica

```python
from app.database.domain.orchestrator import inicializar_banco

# Inicializa tudo automaticamente
inicializar_banco()
```

### Inicialização Customizada

```python
from app.database.domain.orchestrator import DatabaseOrchestrator

orchestrator = DatabaseOrchestrator()

# Verificar se já está inicializado
if not orchestrator.verificar_banco_inicializado():
    # Inicializar apenas infraestrutura
    orchestrator.inicializar_infraestrutura()
    
    # Inicializar apenas um domínio específico
    from app.database.domain.registry import get_registry
    registry = get_registry()
    cadastros = registry.get("cadastros")
    if cadastros:
        cadastros.initialize()
```

### Verificar Domínios Registrados

```python
from app.database.domain.registry import get_registry

registry = get_registry()
print(f"Domínios registrados: {registry.count()}")

for initializer in registry.get_all():
    print(f"- {initializer.get_domain_name()}")
```

## Exemplos Avançados

### Inicializador com Validação Customizada

```python
class MeuDominioInitializer(DomainInitializer):
    def validate(self) -> bool:
        from sqlalchemy import text
        from app.database.db_connection import engine
        
        try:
            with engine.connect() as conn:
                # Verifica se tabela específica existe
                result = conn.execute(text("""
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'meu_dominio' 
                    AND table_name = 'tabela_importante'
                """))
                return result.scalar() is not None
        except Exception:
            return False
```

### Inicializador com Ordem Específica de Tabelas

```python
class MeuDominioInitializer(DomainInitializer):
    def initialize_tables(self) -> None:
        from app.database.db_connection import engine, Base
        
        # Define ordem específica
        tabelas_ordenadas = [
            TabelaBaseModel.__table__,
            TabelaDependenteModel.__table__,
        ]
        
        for table in tabelas_ordenadas:
            table.create(engine, checkfirst=True)
        
        # Depois cria as demais
        super().initialize_tables()
```

### Inicializador com Dados Iniciais Complexos

```python
class MeuDominioInitializer(DomainInitializer):
    def initialize_data(self) -> None:
        from sqlalchemy.dialects.postgresql import insert
        from app.database.db_connection import SessionLocal
        from app.api.meu_dominio.models import MeuModel
        
        with SessionLocal() as session:
            # Insere dados padrão
            stmt = insert(MeuModel).values([
                {"campo1": "valor1", "campo2": "valor2"},
                {"campo1": "valor3", "campo2": "valor4"},
            ]).on_conflict_do_nothing()
            
            session.execute(stmt)
            session.commit()
```

## Migração do Código Antigo

Para migrar o código antigo (`init_db.py`):

1. **Identifique as responsabilidades por domínio**
   - Quais tabelas pertencem a qual domínio?
   - Quais dados iniciais são específicos de cada domínio?

2. **Crie os inicializadores**
   - Um inicializador por domínio
   - Mova a lógica de criação de tabelas
   - Mova a lógica de dados iniciais

3. **Atualize o ponto de entrada**
   - Use `inicializar_banco()` do orquestrador
   - Importe todos os inicializadores

4. **Teste**
   - Verifique se todas as tabelas são criadas
   - Verifique se os dados iniciais são populados
   - Teste em ambiente de desenvolvimento primeiro

## Benefícios

✅ **Modularidade**: Cada domínio é independente  
✅ **Manutenibilidade**: Fácil encontrar e modificar código  
✅ **Testabilidade**: Teste domínios isoladamente  
✅ **Extensibilidade**: Adicione novos domínios facilmente  
✅ **Clareza**: Responsabilidades bem definidas

