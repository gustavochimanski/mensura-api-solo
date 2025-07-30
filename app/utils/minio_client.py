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


def gerar_nome_bucket(cnpj: str) -> str:
    """
    Gera um nome de bucket seguro e válido com base no CNPJ ou nome da empresa.
    """
    return slugify(cnpj)[:63]  # garante no máximo 63 caracteres


def upload_file_to_minio(
    db: Session,
    cod_empresa: int,
    file: UploadFile,
    slug: str
) -> str:
    # 1️⃣ Busca e limpa o CNPJ
    repo = EmpresaRepository(db)
    cnpj = repo.get_cnpj_by_id(cod_empresa)

    if not cnpj:
        raise ValueError(f"Empresa {cod_empresa} não possui CNPJ cadastrado.")

    # 2️⃣ Garante bucket com nome igual ao CNPJ
    bucket_name = gerar_nome_bucket(cnpj)

    if not bucket_name:
        raise ValueError(f"Falha ao gerar nome do bucket para CNPJ: {cnpj}")

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



def remover_arquivo_minio(url: str) -> None:
    """
    Remove um arquivo do MinIO com base na URL completa salva no banco (ex: imagem da categoria).
    """
    if not url or not MINIO_PUBLIC_ENDPOINT:
        return

    try:
        # Remove o domínio da URL pública e extrai bucket e objeto
        base_url = MINIO_PUBLIC_ENDPOINT.rstrip("/")
        relative_path = url.replace(base_url, "").lstrip("/")  # exemplo: cnpj-do-cliente/imagens/abc.png

        parts = relative_path.split("/", 1)
        if len(parts) != 2:
            raise ValueError("URL malformada para remoção no MinIO")

        bucket_name, object_key = parts
        client.remove_object(bucket_name, object_key)
        print(f"✅ Removido: {bucket_name}/{object_key}")

    except Exception as e:
        print(f"⚠️ Erro ao remover arquivo do MinIO: {e}")
