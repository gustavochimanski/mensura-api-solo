import uuid
import mimetypes
from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

# ========== CARREGAR .env ==========
import os

from app.utils.logger import logger

# Só carrega .env se estiver fora do Docker
if not os.getenv("RUNNING_IN_DOCKER"):
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")


# ========== CONFIGURAÇÃO ==========
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")  # interno: usado para conectar
MINIO_ENDPOINT_CLEAN = (MINIO_ENDPOINT or "").replace("http://", "").replace("https://", "")
MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_ENDPOINT")  # externo: usado para gerar link
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD")

# ========== CLIENT ==========
client = Minio(
    endpoint=MINIO_ENDPOINT_CLEAN,
    access_key=MINIO_ROOT_USER,
    secret_key=MINIO_ROOT_PASSWORD,
    secure=MINIO_ENDPOINT.startswith("https"),
)

# ========== FUNÇÃO DE UPLOAD ==========
def upload_file_to_minio(file: UploadFile, slug: str, bucket: str) -> str:
    try:
        logger.info(f"🔍 Verificando se o bucket '{bucket}' existe...")
        if not client.bucket_exists(bucket):
            logger.info(f"📦 Bucket '{bucket}' não existe. Criando...")
            client.make_bucket(bucket)
        else:
            logger.info(f"✅ Bucket '{bucket}' já existe.")

        ext = mimetypes.guess_extension(file.content_type) or ".bin"
        filename = f"{uuid.uuid4()}{ext}"

        logger.info(f"⬆️ Upload: bucket='{bucket}', filename='{filename}'")

        client.put_object(
            bucket_name=bucket,
            object_name=filename,
            data=file.file,
            length=-1,
            part_size=10 * 1024 * 1024,
            content_type=file.content_type,
        )

        # ⚠️ Aqui agora usamos o endpoint PÚBLICO
        url = f"{MINIO_PUBLIC_ENDPOINT}/{bucket}/{filename}"
        logger.info(f"✅ Upload finalizado com sucesso: {url}")
        return url

    except S3Error as e:
        logger.error(f"❌ Erro MinIO: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Erro inesperado: {e}")
        raise
