"""
Classe base abstrata para inicializadores de domínio.
"""
from abc import ABC, abstractmethod
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DomainInitializer(ABC):
    """
    Classe base para inicializadores de domínio.
    
    Cada domínio deve criar uma subclasse implementando os métodos abstratos.
    """
    
    @abstractmethod
    def get_domain_name(self) -> str:
        """
        Retorna o nome do domínio (para logging e identificação).
        
        Returns:
            str: Nome do domínio (ex: "cadastros", "cardapio")
        """
        pass
    
    @abstractmethod
    def get_schema_name(self) -> str:
        """
        Retorna o nome do schema do banco de dados.
        
        Returns:
            str: Nome do schema (ex: "cadastros", "cardapio")
        """
        pass
    
    def initialize_tables(self) -> None:
        """
        Cria as tabelas do domínio.
        
        Implementação padrão: cria todas as tabelas do schema.
        Pode ser sobrescrito para lógica customizada.
        """
        from app.database.db_connection import engine, Base
        
        schema_name = self.get_schema_name()
        
        # Usa sorted_tables que respeita dependências (ordem topológica)
        tables_to_create = [
            t for t in Base.metadata.sorted_tables
            if t.schema == schema_name
        ]
        
        if not tables_to_create:
            logger.warning(f"⚠️ Nenhuma tabela encontrada para o schema '{schema_name}'. Verifique se os models foram importados.")
            return
        
        logger.info(f"📋 Criando {len(tables_to_create)} tabela(s) do domínio {self.get_domain_name()}...")
        
        for table in tables_to_create:
            try:
                table.create(engine, checkfirst=True)
                logger.info(f"  ✅ Tabela {table.schema}.{table.name} criada/verificada")
            except Exception as e:
                error_msg = str(e)
                if "already exists" in error_msg.lower():
                    logger.info(f"  ℹ️ Tabela {table.schema}.{table.name} já existe")
                else:
                    logger.error(f"  ❌ Erro ao criar tabela {table.schema}.{table.name}: {e}")
                    raise
    
    def initialize_data(self) -> None:
        """
        Popula dados iniciais do domínio (opcional).
        
        Implementação padrão: não faz nada.
        Pode ser sobrescrito para popular dados iniciais.
        """
        pass
    
    def validate(self) -> bool:
        """
        Valida se o domínio foi inicializado corretamente (opcional).
        
        Returns:
            bool: True se válido, False caso contrário
        """
        return True
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Método principal de inicialização chamado pelo orquestrador.
        
        Implementação padrão chama initialize_tables() e initialize_data().
        Pode ser sobrescrito para lógica customizada.
        """
        logger.info(f"🏗️ Inicializando domínio {self.get_domain_name()}...")
        
        try:
            self.initialize_tables()
            self.initialize_data()
            
            if self.validate():
                logger.info(f"✅ Domínio {self.get_domain_name()} inicializado com sucesso.")
            else:
                logger.warning(f"⚠️ Domínio {self.get_domain_name()} inicializado, mas validação falhou.")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar domínio {self.get_domain_name()}: {e}", exc_info=True)
            raise

