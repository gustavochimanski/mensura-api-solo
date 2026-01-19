# app/utils/minio_utils.py

import uuid
import mimetypes
import os
from urllib.parse import urlparse

from slugify import slugify

from fastapi import UploadFile
from minio import Minio
from sqlalchemy.orm import Session

from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.utils.logger import logger

# Só carrega .env se não estiver em Docker
if not os.getenv("RUNNING_IN_DOCKER"):
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

# Configuração do MinIO Client
# Usa o endpoint interno (nome do container + porta interna)
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_ENDPOINT", "")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "")

def criar_cliente_minio():
    """Cria um cliente MinIO com as configurações do ambiente."""
    return Minio(
        endpoint=MINIO_ENDPOINT,
        access_key=MINIO_ROOT_USER,
        secret_key=MINIO_ROOT_PASSWORD,
        secure=MINIO_ENDPOINT.startswith("https")
    )


def verificar_conexao_minio() -> bool:
    """
    Verifica se o MinIO está acessível.
    Retorna True se conseguir conectar, False caso contrário.
    """
    try:
        client = criar_cliente_minio()
        # Tenta listar buckets como teste de conexão
        client.list_buckets()
        return True
    except Exception as e:
        logger.warning(f"[MinIO] Não foi possível conectar ao MinIO em {MINIO_ENDPOINT}: {e}")
        return False


# Cliente MinIO global (lazy initialization)
client = None


def get_minio_client():
    """Obtém o cliente MinIO, criando se necessário."""
    global client
    if client is None:
        client = criar_cliente_minio()
    return client


def gerar_nome_bucket(cnpj: str) -> str:
    """
    Gera um nome de bucket seguro e válido com base no CNPJ ou nome da empresa.
    """
    return slugify(cnpj)[:63]


def configurar_permissoes_bucket(bucket_name: str) -> bool:
    """
    Configura permissões públicas de download para um bucket do MinIO.
    Retorna True se configurado com sucesso, False caso contrário.
    """
    try:
        logger.info(f"[MinIO] Configurando permissões públicas para bucket: {bucket_name}")
        
        client = get_minio_client()
        
        # Verifica se o bucket existe
        if not client.bucket_exists(bucket_name):
            logger.warning(f"[MinIO] Bucket não existe para configurar permissões: {bucket_name}")
            return False
        
        # Configura política pública para download
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        
        import json
        client.set_bucket_policy(bucket_name, json.dumps(policy))
        logger.info(f"[MinIO] Permissões públicas configuradas com sucesso para bucket: {bucket_name}")
        return True
        
    except Exception as e:
        logger.error(f"[MinIO] Erro ao configurar permissões do bucket {bucket_name}: {e}")
        return False




def upload_file_to_minio(
    db: Session,
    cod_empresa: int,
    file: UploadFile,
    slug: str
) -> str:
    logger.info(f"[MinIO] Iniciando upload - empresa_id={cod_empresa}, slug={slug}, content_type={file.content_type}")
    
    # 1️⃣ Busca CNPJ
    repo = EmpresaRepository(db)
    cnpj = repo.get_cnpj_by_id(cod_empresa)
    if not cnpj:
        logger.error(f"[MinIO] Empresa {cod_empresa} não possui CNPJ cadastrado")
        raise ValueError(f"Empresa {cod_empresa} não possui CNPJ cadastrado.")

    logger.info(f"[MinIO] CNPJ encontrado: {cnpj}")

    # 2️⃣ Verifica conexão com MinIO
    if not verificar_conexao_minio():
        error_msg = f"MinIO não está acessível em {MINIO_ENDPOINT}. Verifique se o serviço está rodando e se as variáveis de ambiente estão configuradas corretamente."
        logger.error(f"[MinIO] {error_msg}")
        raise ConnectionError(error_msg)

    # 3️⃣ Bucket
    bucket_name = gerar_nome_bucket(cnpj)
    if not bucket_name:
        logger.error(f"[MinIO] Falha ao gerar nome de bucket para CNPJ: {cnpj}")
        raise ValueError(f"Falha ao gerar nome de bucket para CNPJ: {cnpj}")
    
    logger.info(f"[MinIO] Nome do bucket: {bucket_name}")
    
    client = get_minio_client()
    
    if not client.bucket_exists(bucket_name):
        logger.info(f"[MinIO] Criando bucket: {bucket_name}")
        client.make_bucket(bucket_name)
        # Configura permissões públicas automaticamente para novos buckets
        configurar_permissoes_bucket(bucket_name)
    else:
        logger.info(f"[MinIO] Bucket já existe: {bucket_name}")
        # Verifica e configura permissões se necessário
        try:
            # Tenta acessar a política do bucket para verificar se já está configurada
            client.get_bucket_policy(bucket_name)
        except Exception:
            # Se não conseguir obter a política, configura as permissões
            logger.info(f"[MinIO] Configurando permissões para bucket existente: {bucket_name}")
            configurar_permissoes_bucket(bucket_name)

    # 3️⃣ Usa o arquivo original
    file_data = file.file
    content_type = file.content_type

    # 4️⃣ Nome do objeto
    ext = mimetypes.guess_extension(content_type) or ".bin"
    filename = f"{uuid.uuid4()}{ext}"
    object_key = f"{slug}/{filename}"
    
    logger.info(f"[MinIO] Nome do objeto: {object_key}")

    # 5️⃣ Upload
    try:
        client.put_object(
            bucket_name=bucket_name,
            object_name=object_key,
            data=file_data,
            length=-1,
            part_size=10 * 1024 * 1024,
            content_type=content_type,
        )
        logger.info(f"[MinIO] Upload concluído com sucesso")
    except Exception as e:
        logger.error(f"[MinIO] Erro no upload: {e}")
        raise

    # 6️⃣ URL pública
    url = f"{MINIO_PUBLIC_ENDPOINT}/{bucket_name}/{object_key}"
    logger.info(f"[MinIO] URL gerada: {url}")
    return url


def update_file_to_minio(
    db: Session,
    cod_empresa: int,
    file: UploadFile,
    slug: str,
    url_antiga: str = None
) -> str:
    """
    Atualiza um arquivo no MinIO, removendo o arquivo antigo se fornecido.
    Retorna a nova URL do arquivo.
    """
    logger.info(f"[MinIO] Iniciando update - empresa_id={cod_empresa}, slug={slug}, url_antiga={url_antiga}")
    
    # 1️⃣ Faz upload do novo arquivo
    nova_url = upload_file_to_minio(db, cod_empresa, file, slug)
    
    # 2️⃣ Remove o arquivo antigo se fornecido e diferente do novo
    if url_antiga and url_antiga != nova_url:
        try:
            remover_arquivo_minio(url_antiga)
            logger.info(f"[MinIO] Arquivo antigo removido com sucesso: {url_antiga}")
        except Exception as e:
            logger.warning(f"[MinIO] Falha ao remover arquivo antigo: {e} | url={url_antiga}")
    
    return nova_url


def remover_arquivo_minio(file_url: str) -> bool:
    """
    Remove um arquivo do MinIO baseado na URL.
    Retorna True se removido com sucesso, False caso contrário.
    """
    if not file_url:
        logger.warning("[MinIO] URL vazia fornecida para remoção")
        return False

    try:
        logger.info(f"[MinIO] Iniciando remoção - URL: {file_url}")
        
        # Parse da URL
        u = urlparse(file_url)
        path_parts = [p for p in u.path.split("/") if p]  # remove vazios

        if len(path_parts) < 2:
            logger.error(f"[MinIO] Caminho inválido para remover do MinIO: {file_url}")
            return False

        bucket_name = path_parts[0]
        object_key = "/".join(path_parts[1:])
        
        logger.info(f"[MinIO] Tentando remover - bucket: {bucket_name}, key: {object_key}")

        client = get_minio_client()
        
        # Verifica se o bucket existe antes de tentar remover
        if not client.bucket_exists(bucket_name):
            logger.warning(f"[MinIO] Bucket não existe: {bucket_name}")
            return False

        # Remove o objeto
        client.remove_object(bucket_name, object_key)
        logger.info(f"[MinIO] Arquivo removido com sucesso - bucket: {bucket_name}, key: {object_key}")
        return True
        
    except Exception as e:
        logger.error(f"[MinIO] Erro ao remover arquivo: {e} | URL: {file_url}")
        return False


def corrigir_permissoes_todos_buckets() -> dict:
    """
    Corrige permissões de todos os buckets existentes no MinIO.
    Retorna um dicionário com o status de cada bucket.
    """
    resultado = {
        "buckets_processados": 0,
        "sucessos": 0,
        "falhas": 0,
        "detalhes": []
    }
    
    try:
        logger.info("[MinIO] Iniciando correção de permissões para todos os buckets")
        
        # Verifica conexão
        if not verificar_conexao_minio():
            logger.error(f"[MinIO] Não foi possível conectar ao MinIO em {MINIO_ENDPOINT}")
            return {
                "buckets_processados": 0,
                "sucessos": 0,
                "falhas": 0,
                "detalhes": [],
                "erro_geral": f"MinIO não está acessível em {MINIO_ENDPOINT}"
            }
        
        client = get_minio_client()
        
        # Lista todos os buckets
        buckets = client.list_buckets()
        
        for bucket in buckets:
            bucket_name = bucket.name
            resultado["buckets_processados"] += 1
            
            try:
                logger.info(f"[MinIO] Processando bucket: {bucket_name}")
                
                # Verifica se já tem política configurada
                try:
                    client.get_bucket_policy(bucket_name)
                    logger.info(f"[MinIO] Bucket {bucket_name} já possui política configurada")
                    resultado["detalhes"].append({
                        "bucket": bucket_name,
                        "status": "já_configurado",
                        "mensagem": "Política já configurada"
                    })
                except Exception:
                    # Configura permissões se não tiver
                    if configurar_permissoes_bucket(bucket_name):
                        resultado["sucessos"] += 1
                        resultado["detalhes"].append({
                            "bucket": bucket_name,
                            "status": "configurado",
                            "mensagem": "Permissões configuradas com sucesso"
                        })
                    else:
                        resultado["falhas"] += 1
                        resultado["detalhes"].append({
                            "bucket": bucket_name,
                            "status": "erro",
                            "mensagem": "Falha ao configurar permissões"
                        })
                        
            except Exception as e:
                resultado["falhas"] += 1
                logger.error(f"[MinIO] Erro ao processar bucket {bucket_name}: {e}")
                resultado["detalhes"].append({
                    "bucket": bucket_name,
                    "status": "erro",
                    "mensagem": f"Erro: {str(e)}"
                })
        
        logger.info(f"[MinIO] Correção concluída - Processados: {resultado['buckets_processados']}, Sucessos: {resultado['sucessos']}, Falhas: {resultado['falhas']}")
        
    except Exception as e:
        logger.error(f"[MinIO] Erro geral na correção de permissões: {e}")
        resultado["erro_geral"] = str(e)
    
    return resultado

