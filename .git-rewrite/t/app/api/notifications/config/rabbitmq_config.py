"""
Configurações do RabbitMQ para o sistema de notificações
"""

import os
from typing import Dict, Any

# Configurações de conexão RabbitMQ
RABBITMQ_CONFIG = {
    "host": os.getenv("RABBITMQ_HOST", "localhost"),
    "port": int(os.getenv("RABBITMQ_PORT", 5672)),
    "username": os.getenv("RABBITMQ_USERNAME", "guest"),
    "password": os.getenv("RABBITMQ_PASSWORD", "guest"),
    "virtual_host": os.getenv("RABBITMQ_VHOST", "/"),
    "heartbeat": int(os.getenv("RABBITMQ_HEARTBEAT", 600)),
    "blocked_connection_timeout": int(os.getenv("RABBITMQ_BLOCKED_TIMEOUT", 300)),
}

# Configurações de exchanges
EXCHANGES = {
    "notifications": {
        "name": "notifications",
        "type": "topic",
        "durable": True,
        "auto_delete": False
    },
    "events": {
        "name": "events", 
        "type": "topic",
        "durable": True,
        "auto_delete": False
    },
    "dead_letter": {
        "name": "dead_letter",
        "type": "direct",
        "durable": True,
        "auto_delete": False
    }
}

# Configurações de queues
QUEUES = {
    "notifications.email": {
        "name": "notifications.email",
        "durable": True,
        "exclusive": False,
        "auto_delete": False,
        "arguments": {
            "x-dead-letter-exchange": "dead_letter",
            "x-dead-letter-routing-key": "failed"
        }
    },
    "notifications.whatsapp": {
        "name": "notifications.whatsapp",
        "durable": True,
        "exclusive": False,
        "auto_delete": False,
        "arguments": {
            "x-dead-letter-exchange": "dead_letter",
            "x-dead-letter-routing-key": "failed"
        }
    },
    "notifications.webhook": {
        "name": "notifications.webhook",
        "durable": True,
        "exclusive": False,
        "auto_delete": False,
        "arguments": {
            "x-dead-letter-exchange": "dead_letter",
            "x-dead-letter-routing-key": "failed"
        }
    },
    "notifications.push": {
        "name": "notifications.push",
        "durable": True,
        "exclusive": False,
        "auto_delete": False,
        "arguments": {
            "x-dead-letter-exchange": "dead_letter",
            "x-dead-letter-routing-key": "failed"
        }
    },
    "notifications.in_app": {
        "name": "notifications.in_app",
        "durable": True,
        "exclusive": False,
        "auto_delete": False,
        "arguments": {
            "x-dead-letter-exchange": "dead_letter",
            "x-dead-letter-routing-key": "failed"
        }
    },
    "events.processor": {
        "name": "events.processor",
        "durable": True,
        "exclusive": False,
        "auto_delete": False
    },
    "notifications.failed": {
        "name": "notifications.failed",
        "durable": True,
        "exclusive": False,
        "auto_delete": False
    }
}

# Configurações de routing keys
ROUTING_KEYS = {
    "notifications": {
        "email": "notification.email",
        "whatsapp": "notification.whatsapp", 
        "webhook": "notification.webhook",
        "push": "notification.push",
        "in_app": "notification.in_app"
    },
    "events": {
        "all": "event.*",
        "pedido": "event.pedido_*",
        "usuario": "event.usuario_*",
        "sistema": "event.sistema_*",
        "pagamento": "event.pagamento_*"
    },
    "dead_letter": {
        "failed": "failed"
    }
}

# Configurações de QoS
QOS_CONFIG = {
    "prefetch_count": int(os.getenv("RABBITMQ_PREFETCH_COUNT", 1)),
    "prefetch_size": int(os.getenv("RABBITMQ_PREFETCH_SIZE", 0)),
    "global_qos": os.getenv("RABBITMQ_GLOBAL_QOS", "false").lower() == "true"
}

# Configurações de retry
RETRY_CONFIG = {
    "max_retries": int(os.getenv("RABBITMQ_MAX_RETRIES", 3)),
    "retry_delay": int(os.getenv("RABBITMQ_RETRY_DELAY", 5)),  # segundos
    "exponential_backoff": os.getenv("RABBITMQ_EXPONENTIAL_BACKOFF", "true").lower() == "true"
}

# Configurações de monitoramento
MONITORING_CONFIG = {
    "enable_metrics": os.getenv("RABBITMQ_ENABLE_METRICS", "true").lower() == "true",
    "metrics_interval": int(os.getenv("RABBITMQ_METRICS_INTERVAL", 60)),  # segundos
    "health_check_interval": int(os.getenv("RABBITMQ_HEALTH_CHECK_INTERVAL", 30))  # segundos
}

# Configurações de segurança
SECURITY_CONFIG = {
    "ssl_enabled": os.getenv("RABBITMQ_SSL_ENABLED", "false").lower() == "true",
    "ssl_cert_path": os.getenv("RABBITMQ_SSL_CERT_PATH"),
    "ssl_key_path": os.getenv("RABBITMQ_SSL_KEY_PATH"),
    "ssl_ca_path": os.getenv("RABBITMQ_SSL_CA_PATH"),
    "ssl_verify": os.getenv("RABBITMQ_SSL_VERIFY", "true").lower() == "true"
}

def get_rabbitmq_url() -> str:
    """Retorna URL de conexão do RabbitMQ"""
    protocol = "amqps" if SECURITY_CONFIG["ssl_enabled"] else "amqp"
    
    return f"{protocol}://{RABBITMQ_CONFIG['username']}:{RABBITMQ_CONFIG['password']}@{RABBITMQ_CONFIG['host']}:{RABBITMQ_CONFIG['port']}{RABBITMQ_CONFIG['virtual_host']}"

def get_queue_config(queue_name: str) -> Dict[str, Any]:
    """Retorna configuração de uma queue"""
    return QUEUES.get(queue_name, {})

def get_exchange_config(exchange_name: str) -> Dict[str, Any]:
    """Retorna configuração de um exchange"""
    return EXCHANGES.get(exchange_name, {})

def get_routing_key(queue_name: str) -> str:
    """Retorna routing key para uma queue"""
    if queue_name.startswith("notifications."):
        channel = queue_name.split(".")[-1]
        return ROUTING_KEYS["notifications"].get(channel, f"notification.{channel}")
    elif queue_name == "events.processor":
        return ROUTING_KEYS["events"]["all"]
    elif queue_name == "notifications.failed":
        return ROUTING_KEYS["dead_letter"]["failed"]
    else:
        return queue_name
