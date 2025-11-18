"""
Versão refatorada do init_db.py usando o novo sistema de domínios.

Este arquivo mantém compatibilidade com o código existente enquanto
usa a nova arquitetura de domínios internamente.
"""
import logging

# Importa os inicializadores de domínios para garantir registro automático
from app.api.cadastros.database import CadastrosInitializer  # noqa: F401
from app.api.cardapio.database import CardapioInitializer  # noqa: F401
from app.api.mesas.database import MesasInitializer  # noqa: F401

# Importa o orquestrador
from app.database.domain.orchestrator import DatabaseOrchestrator, inicializar_banco

logger = logging.getLogger(__name__)


def verificar_banco_inicializado():
    """
    Verifica se o banco já foi inicializado.
    
    Mantém compatibilidade com código existente.
    """
    orchestrator = DatabaseOrchestrator()
    return orchestrator.verificar_banco_inicializado()


def inicializar_banco_completo():
    """
    Função principal de inicialização do banco.
    
    Esta função usa o novo sistema de domínios mas mantém
    a mesma interface do código antigo.
    """
    inicializar_banco()


# Mantém a função original para compatibilidade
if __name__ == "__main__":
    inicializar_banco_completo()

