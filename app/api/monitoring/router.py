"""
Router para monitoramento e visualização de logs.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pathlib import Path
from datetime import datetime
import re
from app.database.db_connection import get_db
from app.core.admin_dependencies import get_current_user
from app.utils.prometheus_metrics import get_metrics, CONTENT_TYPE_LATEST
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/monitoring",
    tags=["Monitoring - Monitoramento"]
)

# Router público para métricas (sem autenticação)
router_public = APIRouter(
    prefix="/api/monitoring",
    tags=["Monitoring - Monitoramento"]
)

# Caminho do arquivo de log
BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"


@router_public.get("/metrics")
async def metrics():
    """
    Endpoint de métricas Prometheus (público, sem autenticação).
    Acesse em: /api/monitoring/metrics
    """
    return StreamingResponse(
        iter([get_metrics()]),
        media_type=CONTENT_TYPE_LATEST
    )


@router.get("/logs", response_class=HTMLResponse)
async def view_logs(
    lines: int = Query(100, ge=1, le=1000, description="Número de linhas para exibir"),
    level: Optional[str] = Query(None, description="Filtrar por nível (INFO, ERROR, WARNING, DEBUG)"),
    search: Optional[str] = Query(None, description="Buscar texto nas linhas"),
):
    """
    Visualiza logs da aplicação via web.
    Acesse em: /api/monitoring/logs?lines=100&level=ERROR&search=erro
    """
    try:
        if not LOG_FILE.exists():
            return HTMLResponse(
                content="<h1>Arquivo de log não encontrado</h1>",
                status_code=404
            )
        
        # Lê as últimas N linhas do arquivo
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        # Pega as últimas linhas
        log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        # Filtra por nível - procura [LEVEL] em qualquer lugar da linha (case insensitive)
        if level:
            level_upper = level.upper()
            # Procura por [ERROR], [WARNING], etc. em qualquer lugar da linha
            log_lines = [line for line in log_lines if f"[{level_upper}]" in line.upper()]
        
        # Filtra por busca
        if search:
            log_lines = [line for line in log_lines if search.lower() in line.lower()]
        
        # Formata as linhas
        formatted_lines = []
        for line in log_lines:
            # Extrai informações da linha
            original_line = line
            line = line.strip()
            if not line:
                continue
            
            # Detecta nível de log - procura em qualquer lugar da linha
            # Formato pode ser: [INFO] [timestamp] [ERROR] ou [ERROR] [timestamp] ou [timestamp] [ERROR]
            log_level = "INFO"
            line_upper = line.upper()
            
            # Prioriza ERROR, depois WARNING, depois DEBUG, depois INFO
            if "[ERROR]" in line_upper:
                log_level = "ERROR"
                color = "#ff6b6b"
                bg_color = "#2d1b1b"
            elif "[WARNING]" in line_upper or "[WARN]" in line_upper:
                log_level = "WARNING"
                color = "#ffd93d"
                bg_color = "#2d2b1b"
            elif "[DEBUG]" in line_upper:
                log_level = "DEBUG"
                color = "#95a5a6"
                bg_color = "#1e1e1e"
            else:
                log_level = "INFO"
                color = "#4ecdc4"
                bg_color = "#1e1e1e"
            
            # Escapa HTML
            line_escaped = line.replace("<", "&lt;").replace(">", "&gt;")
            
            # Destaque especial para erros
            if log_level == "ERROR":
                formatted_lines.append(
                    f'<div style="color: {color}; background-color: {bg_color}; margin: 3px 0; padding: 8px; font-family: monospace; font-size: 12px; border-left: 4px solid {color}; border-radius: 3px;">'
                    f'<span style="font-weight: bold; color: {color};">[{log_level}]</span> {line_escaped}'
                    f'</div>'
                )
            else:
                formatted_lines.append(
                    f'<div style="color: {color}; margin: 2px 0; padding: 4px; font-family: monospace; font-size: 12px; border-left: 3px solid {color};">'
                    f'<span style="font-weight: bold; color: {color};">[{log_level}]</span> {line_escaped}'
                    f'</div>'
                )
        
        # HTML da página
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Logs da Aplicação</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                }}
                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                }}
                h1 {{
                    color: #4ec9b0;
                    border-bottom: 2px solid #4ec9b0;
                    padding-bottom: 10px;
                }}
                .controls {{
                    background-color: #252526;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                    display: flex;
                    gap: 15px;
                    flex-wrap: wrap;
                    align-items: center;
                }}
                .controls label {{
                    color: #cccccc;
                    font-weight: bold;
                }}
                .controls input, .controls select {{
                    padding: 8px;
                    border: 1px solid #3e3e42;
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                    border-radius: 3px;
                }}
                .controls button {{
                    padding: 8px 20px;
                    background-color: #0e639c;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    cursor: pointer;
                    font-weight: bold;
                }}
                .controls button:hover {{
                    background-color: #1177bb;
                }}
                .log-container {{
                    background-color: #1e1e1e;
                    border: 1px solid #3e3e42;
                    border-radius: 5px;
                    padding: 15px;
                    max-height: 80vh;
                    overflow-y: auto;
                    font-family: 'Courier New', monospace;
                }}
                .log-line {{
                    margin: 2px 0;
                    padding: 2px 5px;
                    border-left: 3px solid transparent;
                }}
                .log-line:hover {{
                    background-color: #2a2d2e;
                }}
                .stats {{
                    background-color: #252526;
                    padding: 10px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                    color: #cccccc;
                }}
                .auto-refresh {{
                    margin-left: auto;
                }}
                .auto-refresh label {{
                    display: flex;
                    align-items: center;
                    gap: 5px;
                }}
            </style>
            <script>
                function autoRefresh() {{
                    if (document.getElementById('auto-refresh').checked) {{
                        setTimeout(function() {{
                            location.reload();
                        }}, 5000);
                    }}
                }}
                setInterval(autoRefresh, 5000);
            </script>
        </head>
        <body>
            <div class="container">
                <h1>📊 Logs da Aplicação</h1>
                
                <div class="stats">
                    <strong>Total de linhas exibidas:</strong> {len(formatted_lines)} | 
                    <strong>Arquivo:</strong> {LOG_FILE} |
                    <strong>Última atualização:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
                
                <div class="controls">
                    <form method="get" action="/api/monitoring/logs" style="display: flex; gap: 15px; flex-wrap: wrap; align-items: center;">
                        <label>Linhas:</label>
                        <input type="number" name="lines" value="{lines}" min="1" max="1000" style="width: 80px;">
                        
                        <label>Nível:</label>
                        <select name="level">
                            <option value="">Todos</option>
                            <option value="ERROR" {'selected' if level == 'ERROR' else ''}>⚠️ ERROR (Apenas erros)</option>
                            <option value="WARNING" {'selected' if level == 'WARNING' else ''}>⚠️ WARNING</option>
                            <option value="INFO" {'selected' if level == 'INFO' else ''}>ℹ️ INFO</option>
                            <option value="DEBUG" {'selected' if level == 'DEBUG' else ''}>🔍 DEBUG</option>
                        </select>
                        
                        <label>Buscar:</label>
                        <input type="text" name="search" value="{search or ''}" placeholder="Texto para buscar" style="width: 200px;">
                        
                        <button type="submit">Atualizar</button>
                        <a href="/api/monitoring/logs?lines={lines}&level=ERROR" style="padding: 8px 15px; background-color: #ff4444; color: white; text-decoration: none; border-radius: 3px; font-weight: bold;">🔴 Apenas Erros</a>
                    </form>
                    
                    <div class="auto-refresh">
                        <label>
                            <input type="checkbox" id="auto-refresh" checked>
                            Auto-refresh (5s)
                        </label>
                    </div>
                </div>
                
                <div class="log-container">
                    {''.join(formatted_lines) if formatted_lines else '<div style="color: #888;">Nenhum log encontrado com os filtros aplicados.</div>'}
                </div>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Erro ao ler logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao ler logs: {str(e)}"
        )


@router.get("/logs/json")
async def get_logs_json(
    lines: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    _current_user=Depends(get_current_user)
):
    """
    Retorna logs em formato JSON.
    """
    try:
        if not LOG_FILE.exists():
            raise HTTPException(status_code=404, detail="Arquivo de log não encontrado")
        
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        if level:
            log_lines = [line for line in log_lines if f"[{level}]" in line.upper()]
        
        if search:
            log_lines = [line for line in log_lines if search.lower() in line.lower()]
        
        # Parse das linhas
        parsed_logs = []
        for line in log_lines:
            line = line.strip()
            if not line:
                continue
            
            # Extrai timestamp, nível e mensagem
            match = re.match(r'\[(.*?)\] \[(.*?)\] (.*?): (.*)', line)
            if match:
                timestamp, log_level, logger_name, message = match.groups()
                parsed_logs.append({
                    "timestamp": timestamp,
                    "level": log_level,
                    "logger": logger_name,
                    "message": message
                })
            else:
                parsed_logs.append({
                    "raw": line
                })
        
        return {
            "total": len(parsed_logs),
            "lines": lines,
            "filters": {
                "level": level,
                "search": search
            },
            "logs": parsed_logs
        }
        
    except Exception as e:
        logger.error(f"Erro ao ler logs JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao ler logs: {str(e)}"
        )

