# app/utils/minio_utils.py
import uuid
import mimetypes
import os

from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error
from sqlalchemy.orm import Session

from app.api.mensura.repositories.empresasRepository import EmpresasRepository
from app.utils.logger import logger

# Só carrega .env se não estiver em Docker
if not os.getenv("RUNNING_IN_DOCKER"):
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

# Configuração do MinIO Client
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "")
MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_ENDPOINT", "")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "")

client = Minio(
    endpoint=MINIO_ENDPOINT.replace("http://", "").replace("https://", ""),
    access_key=MINIO_ROOT_USER,
    secret_key=MINIO_ROOT_PASSWORD,
    secure=MINIO_ENDPOINT.startswith("https"),
)

def upload_file_to_minio(
    db: Session,
    cod_empresa: int,
    file: UploadFile,
    slug: str
) -> str:
    # 1️⃣ Busca e limpa o CNPJ
    repo = EmpresasRepository(db)
    cnpj = repo.get_cnpj_by_id(cod_empresa)

    # 2️⃣ Garante bucket com nome igual ao CNPJ
    bucket_name = cnpj
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)

    # 3️⃣ Gera nome de arquivo e prefixa com slug
    ext = mimetypes.guess_extension(file.content_type) or ".bin"
    filename = f"{uuid.uuid4()}{ext}"
    object_key = f"{slug}/{filename}"  # ex: "meu-slug/uuid.png"

    # 4️⃣ Faz o upload
    client.put_object(
        bucket_name=bucket_name,
        object_name=object_key,
        data=file.file,
        length=-1,
        part_size=10 * 1024 * 1024,
        content_type=file.content_type,
    )

    # 5️⃣ Retorna a URL pública
    return f"{MINIO_PUBLIC_ENDPOINT}/{bucket_name}/{object_key}"
