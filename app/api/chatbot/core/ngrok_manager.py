"""
Gerenciamento do túnel ngrok para webhooks do WhatsApp
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Import pyngrok opcionalmente
try:
    from pyngrok import ngrok, conf
    PYNGROK_AVAILABLE = True
except ImportError:
    PYNGROK_AVAILABLE = False
    ngrok = None
    conf = None
    logger.warning("pyngrok não está instalado. Funcionalidades do ngrok estarão desabilitadas.")

# Variável global para armazenar o túnel ativo
_active_tunnel = None
_public_url: Optional[str] = None


def get_ngrok_authtoken() -> Optional[str]:
    """
    Obtém o authtoken do ngrok das variáveis de ambiente.
    Retorna None se não configurado.
    """
    return os.getenv("NGROK_AUTHTOKEN")


def start_ngrok_tunnel(port: int = 8000) -> Optional[str]:
    """
    Inicia um túnel ngrok para o webhook do WhatsApp.

    Args:
        port: Porta local onde a API está rodando (padrão: 8000)

    Returns:
        URL pública do ngrok ou None se falhar
    """
    global _active_tunnel, _public_url

    if not PYNGROK_AVAILABLE:
        logger.error("pyngrok não está instalado. Instale com: pip install pyngrok")
        return None

    try:
        # Verifica se já existe um túnel ativo
        if _active_tunnel is not None:
            logger.info(f"Túnel ngrok já ativo em: {_public_url}")
            return _public_url

        # Configurar authtoken se disponível
        authtoken = get_ngrok_authtoken()
        if authtoken:
            conf.get_default().auth_token = authtoken
            logger.info("✅ Ngrok authtoken configurado")
        else:
            logger.warning("⚠️  NGROK_AUTHTOKEN não configurado. Usando modo gratuito (túnel pode expirar)")

        # Domínio estático do ngrok
        static_domain = os.getenv("NGROK_DOMAIN")
        
        # Iniciar túnel HTTP
        logger.info(f"🚀 Iniciando túnel ngrok para porta {port}...")
        if static_domain:
            logger.info(f"🔗 Usando domínio estático: {static_domain}")
            tunnel = ngrok.connect(port, bind_tls=True, hostname=static_domain)
        else:
            logger.warning("⚠️  NGROK_DOMAIN não configurado. Usando túnel dinâmico (pode mudar a cada reinicialização)")
            tunnel = ngrok.connect(port, bind_tls=True)

        _active_tunnel = tunnel
        _public_url = tunnel.public_url

        logger.info("=" * 80)
        logger.info("🎉 TÚNEL NGROK ATIVO!")
        logger.info("=" * 80)
        logger.info(f"📍 URL Pública: {_public_url}")
        logger.info(f"📍 Webhook WhatsApp: {_public_url}/api/chatbot/webhook")
        logger.info("=" * 80)
        logger.info("⚙️  PRÓXIMOS PASSOS:")
        logger.info("1. Acesse: https://developers.facebook.com")
        logger.info("2. Vá em 'Meus Apps' > Seu App > WhatsApp > Configuration")
        logger.info(f"3. Configure o webhook com:")
        logger.info(f"   - URL: {_public_url}/api/chatbot/webhook")
        logger.info(f"   - Token de Verificação: meu_token_secreto_123")
        logger.info("=" * 80)

        return _public_url

    except Exception as e:
        logger.error(f"❌ Erro ao iniciar túnel ngrok: {e}")
        logger.error("Verifique se:")
        logger.error("1. ngrok está instalado: pip install pyngrok")
        logger.error("2. Porta 8000 está disponível")
        logger.error("3. NGROK_AUTHTOKEN está configurado (opcional mas recomendado)")
        return None


def stop_ngrok_tunnel():
    """
    Para o túnel ngrok ativo.
    """
    global _active_tunnel, _public_url

    if not PYNGROK_AVAILABLE:
        logger.warning("pyngrok não está instalado. Não é possível parar o túnel.")
        return

    if _active_tunnel:
        try:
            logger.info("🛑 Parando túnel ngrok...")
            ngrok.disconnect(_active_tunnel.public_url)
            _active_tunnel = None
            _public_url = None
            logger.info("✅ Túnel ngrok parado")
        except Exception as e:
            logger.error(f"Erro ao parar túnel ngrok: {e}")


def get_public_url() -> Optional[str]:
    """
    Retorna a URL pública do ngrok se estiver ativo.
    """
    return _public_url


def get_webhook_url() -> Optional[str]:
    """
    Retorna a URL completa do webhook do WhatsApp.
    """
    if _public_url:
        return f"{_public_url}/api/chatbot/webhook"
    return None
