# app/utils/minio_utils.py

import uuid
import mimetypes
import os
from slugify import slugify

from fastapi import UploadFile
from minio import Minio
from sqlalchemy.orm import Session

from app.api.mensura.repositories.empresa_repo import EmpresaRepository

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

    # 3️⃣ Nome do objeto
    ext = mimetypes.guess_extension(file.content_type) or ".bin"
    filename = f"{uuid.uuid4()}{ext}"
    object_key = f"{slug}/{filename}"

    # 4️⃣ Upload
    client.put_object(
        bucket_name=bucket_name,
        object_name=object_key,
        data=file.file,
        length=-1,
        part_size=10 * 1024 * 1024,
        content_type=file.content_type,
    )

    # 5️⃣ URL pública
    return f"{MINIO_PUBLIC_ENDPOINT}/{bucket_name}/{object_key}"


def remover_arquivo_minio(url: str) -> None:
    if not url or not MINIO_PUBLIC_ENDPOINT:
        return
    try:
        base_url = MINIO_PUBLIC_ENDPOINT.rstrip("/")
        relative = url.replace(base_url, "").lstrip("/")
        bucket, obj = relative.split("/", 1)
        client.remove_object(bucket, obj)
    except Exception as e:
        print(f"⚠️ Erro ao remover arquivo do MinIO: {e}")
