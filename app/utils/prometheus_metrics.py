"""
Módulo de métricas Prometheus para monitoramento da aplicação.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
from time import time
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import StreamingResponse
import logging

logger = logging.getLogger(__name__)

# Métricas de requisições HTTP
http_requests_total = Counter(
    'http_requests_total',
    'Total de requisições HTTP',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'Duração das requisições HTTP em segundos',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Métricas de erros
http_errors_total = Counter(
    'http_errors_total',
    'Total de erros HTTP',
    ['method', 'endpoint', 'status_code']
)

# Métricas de aplicação
active_connections = Gauge(
    'active_connections',
    'Número de conexões ativas'
)

# Métricas de logs
log_messages_total = Counter(
    'log_messages_total',
    'Total de mensagens de log',
    ['level']
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware para coletar métricas Prometheus das requisições HTTP."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Ignora o endpoint de métricas para evitar loop
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Ignora o endpoint de logs
        if request.url.path.startswith("/api/monitoring/logs"):
            return await call_next(request)
        
        method = request.method
        endpoint = request.url.path
        
        # Normaliza endpoint (remove IDs para evitar cardinalidade alta)
        normalized_endpoint = self._normalize_endpoint(endpoint)
        
        start_time = time()
        active_connections.inc()
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Registra métricas
            http_requests_total.labels(
                method=method,
                endpoint=normalized_endpoint,
                status_code=status_code
            ).inc()
            
            duration = time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=normalized_endpoint
            ).observe(duration)
            
            # Registra erros (4xx e 5xx)
            if status_code >= 400:
                http_errors_total.labels(
                    method=method,
                    endpoint=normalized_endpoint,
                    status_code=status_code
                ).inc()
            
            return response
            
        except Exception as e:
            status_code = 500
            http_requests_total.labels(
                method=method,
                endpoint=normalized_endpoint,
                status_code=status_code
            ).inc()
            http_errors_total.labels(
                method=method,
                endpoint=normalized_endpoint,
                status_code=status_code
            ).inc()
            raise
        finally:
            active_connections.dec()
    
    def _normalize_endpoint(self, endpoint: str) -> str:
        """
        Normaliza endpoints removendo IDs para evitar alta cardinalidade.
        Ex: /api/users/123 -> /api/users/{id}
        """
        import re
        # Remove UUIDs
        endpoint = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{uuid}', endpoint)
        # Remove IDs numéricos
        endpoint = re.sub(r'/\d+', '/{id}', endpoint)
        return endpoint


def get_metrics():
    """Retorna as métricas no formato Prometheus."""
    return generate_latest()


def record_log(level: str):
    """Registra uma mensagem de log nas métricas."""
    log_messages_total.labels(level=level).inc()

