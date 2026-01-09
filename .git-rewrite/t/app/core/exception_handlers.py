"""
Exception handlers globais para capturar e logar erros da API.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import traceback
import json
from app.utils.logger import logger


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handler para erros de validação (422) do FastAPI/Pydantic.
    Registra os erros detalhados nos logs.
    """
    errors = exc.errors()
    error_details = []
    
    for error in errors:
        field = ".".join(str(loc) for loc in error.get("loc", []))
        error_type = error.get("type", "unknown")
        error_msg = error.get("msg", "Erro de validação")
        error_details.append({
            "field": field,
            "type": error_type,
            "message": error_msg,
            "input": error.get("input")
        })
    
    # Log detalhado do erro
    log_message = (
        f"[VALIDATION ERROR 422] {request.method} {request.url.path} - "
        f"Erros de validação detectados:\n{json.dumps(error_details, indent=2, ensure_ascii=False)}"
    )
    logger.error(log_message)
    
    # Log informações adicionais da requisição
    try:
        query_params = dict(request.query_params)
        if query_params:
            logger.error(f"[VALIDATION ERROR 422] Query params: {json.dumps(query_params, ensure_ascii=False)}")
    except Exception:
        pass
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": error_details,
            "message": "Erro de validação nos dados fornecidos",
            "errors": error_details
        }
    )


async def http_exception_handler(request: Request, exc):
    """
    Handler para HTTPExceptions.
    Registra erros HTTP nos logs com detalhes.
    """
    status_code = exc.status_code
    
    # Log detalhado do erro HTTP
    log_message = (
        f"[HTTP ERROR {status_code}] {request.method} {request.url.path} - "
        f"Detalhes: {exc.detail}"
    )
    
    if status_code >= 500:
        logger.error(log_message)
        try:
            logger.error(f"[HTTP ERROR {status_code}] Traceback: {traceback.format_exc()}")
        except Exception:
            pass
    elif status_code >= 400:
        logger.error(log_message)  # Muda para ERROR para aparecer nos logs
    
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": str(exc.detail),
            "status_code": status_code
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    Handler para exceções não tratadas.
    Registra erros críticos nos logs.
    """
    error_traceback = traceback.format_exc()
    
    log_message = (
        f"[UNHANDLED EXCEPTION] {request.method} {request.url.path} - "
        f"{type(exc).__name__}: {str(exc)}"
    )
    logger.error(log_message)
    logger.error(f"[UNHANDLED EXCEPTION] Traceback completo:\n{error_traceback}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Erro interno do servidor",
            "error_type": type(exc).__name__,
            "message": str(exc)
        }
    )

