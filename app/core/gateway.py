# app/core/gateway.py

from enum import Enum
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.utils.logger import logger


class RouteType(str, Enum):
    """Tipo de rota baseado no contexto de acesso"""
    ADMIN = "admin"
    CLIENT = "client"
    PUBLIC = "public"
    AUTH = "auth"  # Rotas de autenticação (login, token, etc)


def detect_route_type(path: str) -> RouteType:
    """
    Detecta o tipo de rota baseado no path da requisição.
    
    Regras de detecção (em ordem de prioridade):
    1. Rotas especiais (/health, /) -> PUBLIC
    2. /api/auth/* -> AUTH
    3. /api/admin/* ou /api/*/admin/* -> ADMIN
    4. /api/client/* ou /api/*/client/* -> CLIENT
    5. /api/public/* ou /api/*/public/* -> PUBLIC
    6. Presença de "admin", "client" ou "public" no path -> respectivo tipo
    7. Rotas antigas sem prefixo específico: tenta detectar por padrão ou retorna PUBLIC
    """
    path_lower = path.lower()
    
    # 1. Rotas públicas especiais
    if path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
        return RouteType.PUBLIC
    
    # 2. Rotas de autenticação
    if path.startswith("/api/auth"):
        return RouteType.AUTH
    
    # 3. Detecta por prefixo explícito novo (gateway)
    if "/api/admin/" in path_lower or path_lower.startswith("/api/admin/"):
        return RouteType.ADMIN
    
    if "/api/client/" in path_lower or path_lower.startswith("/api/client/"):
        return RouteType.CLIENT
    
    if "/api/public/" in path_lower or path_lower.startswith("/api/public/"):
        return RouteType.PUBLIC
    
    # 4. Detecta por padrão no meio do path (estrutura atual)
    # Exemplos: /api/delivery/admin/pedidos, /api/mensura/admin/usuarios
    path_parts = path_lower.split("/")
    
    # Busca palavras-chave na ordem: admin, client, public
    # Isso garante que /api/delivery/admin/client não seja confundido
    for part in reversed(path_parts):  # Começa do final (mais específico)
        if part == "admin":
            return RouteType.ADMIN
        if part == "client":
            return RouteType.CLIENT
        if part == "public":
            return RouteType.PUBLIC
    
    # 5. Heurística para rotas antigas sem prefixo específico
    # Se não encontrou palavra-chave, assume baseado em rotas conhecidas
    # Isso mantém compatibilidade com rotas antigas
    
    # Rotas que tipicamente são admin (baseado em padrões comuns)
    admin_indicators = ["usuarios", "endereco", "cupons", "acertos", "minio", 
                       "categorias", "receitas", "relatorios", "notifications"]
    for indicator in admin_indicators:
        if indicator in path_parts:
            return RouteType.ADMIN
    
    # Por padrão, considera público se não especificado
    # (permite rotas antigas continuarem funcionando)
    return RouteType.PUBLIC


def validate_route_access(request: Request, route_type: RouteType) -> bool:
    """
    Valida se a requisição tem acesso adequado para o tipo de rota.
    
    Retorna True se o acesso é permitido, False caso contrário.
    Para rotas ADMIN e CLIENT, verifica presença dos tokens apropriados.
    """
    if route_type in [RouteType.PUBLIC, RouteType.AUTH]:
        return True
    
    if route_type == RouteType.ADMIN:
        # Verifica se tem token Bearer no header
        auth_header = request.headers.get("Authorization", "")
        return auth_header.startswith("Bearer ")
    
    if route_type == RouteType.CLIENT:
        # Exceções: endpoints de cadastro/login/novo-dispositivo não exigem super token
        # Ex.: POST /api/cadastros/client/clientes (criar cliente), /novo-dispositivo (login cliente)
        path = request.url.path.lower()
        if path.startswith("/api/cadastros/client/clientes") and request.method.upper() == "POST":
            return True
        if "/novo-dispositivo" in path or "/login" in path or path.startswith("/api/auth"):
            return True

        # Verifica se tem super_token no header (case-insensitive via get)
        return bool(request.headers.get("x-super-token") or request.headers.get("X-Super-Token"))
    
    return False


class GatewayMiddleware(BaseHTTPMiddleware):
    """
    Middleware que atua como gateway, validando acesso às rotas
    baseado no tipo detectado (admin, client, public).
    """
    
    async def dispatch(self, request: Request, call_next):
        # Detecta o tipo de rota
        route_type = detect_route_type(request.url.path)
        
        # Log da requisição
        logger.debug(
            f"[GATEWAY] {request.method} {request.url.path} - Tipo: {route_type.value}"
        )
        
        # Valida acesso (mas não bloqueia - isso é feito pelos dependencies)
        # Este middleware apenas loga e adiciona contexto
        has_access = validate_route_access(request, route_type)
        
        # Adiciona informações no state da requisição para uso posterior
        request.state.route_type = route_type
        request.state.has_valid_auth = has_access
        # Se configurado para bloquear, interrompe aqui quando acesso inválido
        if ENABLE_GATEWAY_BLOCKING and not has_access:
            # Admin/client faltando autenticação -> 401
            if route_type == RouteType.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Autenticação necessária para acessar rota administrativa",
                )
            if route_type == RouteType.CLIENT:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Super token (X-Super-Token) necessário para rotas client",
                )
            # Outros casos -> 403
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso ao recurso negado pelo gateway",
            )

        # Continua com a requisição
        response = await call_next(request)

        # Adiciona header com tipo de rota processada (opcional, para debug)
        if ENABLE_GATEWAY_HEADERS:
            response.headers["X-Route-Type"] = route_type.value

        return response


# Configuração fixa (sem depender de variáveis de ambiente)
# Habilita headers de debug (false por padrão)
ENABLE_GATEWAY_HEADERS = False
# Habilita bloqueio ativo do gateway (True = middleware bloqueará rotas admin/client sem credenciais)
ENABLE_GATEWAY_BLOCKING = True
