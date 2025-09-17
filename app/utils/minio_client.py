# app/utils/minio_utils.py

import uuid
import mimetypes
import os
from urllib.parse import urlparse
from io import BytesIO

from slugify import slugify
from PIL import Image

from fastapi import UploadFile
from minio import Minio
from sqlalchemy.orm import Session

from app.api.mensura.repositories.empresa_repo import EmpresaRepository
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

client = Minio(
    endpoint=MINIO_ENDPOINT,
    access_key=MINIO_ROOT_USER,
    secret_key=MINIO_ROOT_PASSWORD,
    secure=MINIO_ENDPOINT.startswith("https")
)


def gerar_nome_bucket(cnpj: str) -> str:
    """
    Gera um nome de bucket seguro e válido com base no CNPJ ou nome da empresa.
    """
    return slugify(cnpj)[:63]


def redimensionar_imagem(file: UploadFile, slug: str) -> BytesIO:
    """
    Redimensiona imagem baseado no slug:
    - categorias: max 512x512, reduz para 256x256
    - produtos: max 1024x1024, reduz para 512x512
    """
    try:
        # Lê a imagem
        file.file.seek(0)
        image = Image.open(file.file)
        
        # Converte para RGB se necessário (para JPEG)
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Define limites baseado no slug
        if slug == 'categorias':
            max_size = (512, 512)
            target_size = (256, 256)
        elif slug == 'produtos':
            max_size = (1024, 1024)
            target_size = (512, 512)
        else:
            # Para outros slugs, mantém o tamanho original
            return file.file
        
        # Verifica se precisa redimensionar
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            # Redimensiona mantendo proporção
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Reduz para o tamanho alvo
        image = image.resize(target_size, Image.Resampling.LANCZOS)
        
        # Salva em BytesIO
        output = BytesIO()
        image.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        logger.info(f"Imagem redimensionada: {file.size} bytes -> {len(output.getvalue())} bytes")
        return output
        
    except Exception as e:
        logger.warning(f"Erro ao redimensionar imagem: {e}. Usando arquivo original.")
        file.file.seek(0)
        return file.file


def upload_file_to_minio(
    db: Session,
    cod_empresa: int,
    file: UploadFile,
    slug: str
) -> str:
    # 1️⃣ Busca CNPJ
    repo = EmpresaRepository(db)
    cnpj = repo.get_cnpj_by_id(cod_empresa)
    if not cnpj:
        raise ValueError(f"Empresa {cod_empresa} não possui CNPJ cadastrado.")

    # 2️⃣ Bucket
    bucket_name = gerar_nome_bucket(cnpj)
    if not bucket_name:
        raise ValueError(f"Falha ao gerar nome de bucket para CNPJ: {cnpj}")
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)

    # 3️⃣ Processa imagem se for uma imagem
    file_data = file.file
    content_type = file.content_type
    
    # Verifica se é uma imagem e se precisa redimensionar
    if file.content_type and file.content_type.startswith('image/'):
        file_data = redimensionar_imagem(file, slug)
        content_type = 'image/jpeg'  # Sempre salva como JPEG após redimensionamento

    # 4️⃣ Nome do objeto
    ext = mimetypes.guess_extension(content_type) or ".bin"
    filename = f"{uuid.uuid4()}{ext}"
    object_key = f"{slug}/{filename}"

    # 5️⃣ Upload
    client.put_object(
        bucket_name=bucket_name,
        object_name=object_key,
        data=file_data,
        length=-1,
        part_size=10 * 1024 * 1024,
        content_type=content_type,
    )

    # 6️⃣ URL pública
    return f"{MINIO_PUBLIC_ENDPOINT}/{bucket_name}/{object_key}"


def remover_arquivo_minio(file_url: str) -> None:
    if not file_url:
        return

    try:
        from urllib.parse import urlparse
        u = urlparse(file_url)
        path_parts = [p for p in u.path.split("/") if p]  # remove vazios

        if len(path_parts) < 2:
            print(f"⚠️ Caminho inválido para remover do MinIO: {file_url}")
            return

        bucket_name = path_parts[0]  # teste2
        object_key = "/".join(path_parts[1:])  # categorias/f22aac08-...

        client.remove_object(bucket_name, object_key)
        print(f"✅ Removido do MinIO: bucket={bucket_name}, key={object_key}")
    except Exception as e:
        print(f"⚠️ Erro ao remover arquivo do MinIO: {e} | url={file_url}")

