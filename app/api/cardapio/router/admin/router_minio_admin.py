from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.minio_client import corrigir_permissoes_todos_buckets, gerar_nome_bucket, verificar_e_configurar_permissoes, get_minio_client
from app.api.empresas.repositories.empresa_repo import EmpresaRepository

router = APIRouter(prefix="/api/cardapio/admin/minio", tags=["Admin - Cardápio - MinIO"], dependencies=[Depends(get_current_user)])

class EmpresaBucketRequest(BaseModel):
    empresa_id: int

@router.post("/corrigir-permissoes")
def corrigir_permissoes_buckets(db: Session = Depends(get_db)):
    """
    Corrige permissões de todos os buckets do MinIO para permitir acesso público às imagens.
    Útil para resolver erros de "Access Denied" ao acessar imagens.
    """
    resultado = corrigir_permissoes_todos_buckets()
    return resultado

@router.post("/corrigir-empresa/{empresa_id}")
def corrigir_bucket_empresa(empresa_id: int, db: Session = Depends(get_db)):
    """
    Corrige permissões do bucket MinIO para uma empresa específica desconhecida.
    """
    try:
        # Busca dados da empresa
        repo = EmpresaRepository(db)
        empresa = repo.get_empresa_by_id(empresa_id)
        
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        if not empresa.cnpj:
            raise HTTPException(status_code=400, detail="Empresa não possui CNPJ cadastrado")
        
        # Gera nome do bucket
        bucket_name = gerar_nome_bucket(empresa.cnpj)
        
        if not bucket_name:
            raise HTTPException(status_code=400, detail="Falha ao gerar nome do bucket")
        
        # Verifica se bucket existe
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
        
        # Verifica e configura permissões
        sucesso = verificar_e_configurar_permissoes(bucket_name)
        
        return {
            "empresa_id": empresa_id,
            "empresa_nome": empresa.nome,
            "cnpj": empresa.cnpj,
            "bucket_name": bucket_name,
            "configurado": sucesso,
            "mensagem": "Bucket configurado com sucesso" if sucesso else "Falha ao configurar bucket"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao corrigir bucket da empresa: {str(e)}")

@router.get("/verificar-bucket/{empresa_id}")
def verificar_bucket_empresa(empresa_id: int, db: Session = Depends(get_db)):
    """
    Verifica o status do bucket MinIO de uma empresa específica.
    """
    try:
        # Busca dados da empresa
        repo = EmpresaRepository(db)
        empresa = repo.get_empresa_by_id(empresa_id)
        
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        if not empresa.cnpj:
            return {
                "empresa_id": empresa_id,
                "empresa_nome": empresa.nome,
                "cnpj": None,
                "bucket_name": None,
                "bucket_existe": False,
                "tem_politica": False,
                "mensagem": "Empresa não possui CNPJ cadastrado"
            }
        
        # Gera nome do bucket
        bucket_name = gerar_nome_bucket(empresa.cnpj)
        
        if not bucket_name:
            return {
                "empresa_id": empresa_id,
                "empresa_nome": empresa.nome,
                "cnpj": empresa.cnpj,
                "bucket_name": None,
                "bucket_existe": False,
                "tem_politica": False,
                "mensagem": "Falha ao gerar nome do bucket"
            }
        
        # Verifica status do bucket
        client = get_minio_client()
        bucket_existe = client.bucket_exists(bucket_name)
        tem_politica = False
        
        if bucket_existe:
            try:
                policy = client.get_bucket_policy(bucket_name)
                if policy:
                    import json
                    policy_dict = json.loads(policy)
                    statements = policy_dict.get("Statement", [])
                    tem_politica = any(
                        stmt.get("Effect") == "Allow" and 
                        stmt.get("Principal") == "*" and
                        "s3:GetObject" in stmt.get("Action", [])
                        for stmt in statements
                    )
            except:
                tem_politica = False
        
        return {
            "empresa_id": empresa_id,
            "empresa_nome": empresa.nome,
            "cnpj": empresa.cnpj,
            "bucket_name": bucket_name,
            "bucket_existe": bucket_existe,
            "tem_politica": tem_politica,
            "mensagem": "Bucket OK" if (bucket_existe and tem_politica) else "Bucket precisa ser configurado"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao verificar bucket da empresa: {str(e)}")
