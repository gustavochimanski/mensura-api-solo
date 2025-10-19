# app/api/mensura/services/empresa_service.py
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile

from app.api.delivery.models.model_regiao_entrega import RegiaoEntregaModel
from app.api.mensura.models.empresa_model import EmpresaModel
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.mensura.schemas.schema_empresa import (
    EmpresaCreate,
    EmpresaUpdate,
    EmpresaCardapioLinkResponse,
)
from app.api.mensura.schemas.schema_endereco import EnderecoCreate, EnderecoUpdate
from app.api.mensura.services.endereco_service import EnderecoService
from app.utils.minio_client import upload_file_to_minio, remover_arquivo_minio, gerar_nome_bucket, configurar_permissoes_bucket


from app.api.mensura.models.association_tables import entregador_empresa, usuario_empresa
from app.api.mensura.models.cadprod_emp_model import ProdutoEmpModel
from app.api.delivery.models.model_pedido_dv import PedidoDeliveryModel

class EmpresaService:
    def __init__(self, db: Session):
        self.repo_emp = EmpresaRepository(db)
        self.endereco_service = EnderecoService(db)
        self.db = db

    # Recupera empresa
    def get_empresa(self, id: int) -> EmpresaModel:
        empresa = self.repo_emp.get_empresa_by_id(id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        return empresa

    # Lista empresas
    def list_empresas(self, skip: int = 0, limit: int = 100) -> list[EmpresaModel]:
        return self.repo_emp.list(skip, limit)

    def list_cardapio_links(self) -> list[EmpresaCardapioLinkResponse]:
        resultados = self.repo_emp.list_cardapio_links()
        return [
            EmpresaCardapioLinkResponse(
                id=row.id,
                nome=row.nome,
                cardapio_link=row.cardapio_link,
                cardapio_tema=row.cardapio_tema,
            )
            for row in resultados
        ]

    # Cria empresa
    def create_empresa(self, data: EmpresaCreate, logo: UploadFile | None = None):
        # Checa se CNPJ já existe
        if data.cnpj and self.repo_emp.get_emp_by_cnpj(data.cnpj):
            raise HTTPException(status_code=400, detail="Empresa já cadastrada (CNPJ)")

        # Cria endereço
        endereco = self.endereco_service.create_endereco(data.endereco)

        # Cria empresa
        empresa = EmpresaModel(
            nome=data.nome,
            cnpj=data.cnpj,
            slug=data.slug,
            endereco_id=endereco.id,
            cardapio_tema=data.cardapio_tema,
            aceita_pedido_automatico=str(data.aceita_pedido_automatico).lower() == "true",
            tempo_entrega_maximo=data.tempo_entrega_maximo,
        )
        empresa = self.repo_emp.create(empresa)

        # Upload da logo
        if logo:
            empresa.logo = upload_file_to_minio(self.db, empresa.id, logo, "logo")

        # Upload do cardápio
        if data.cardapio_link:
            if isinstance(data.cardapio_link, UploadFile):
                empresa.cardapio_link = upload_file_to_minio(self.db, empresa.id, data.cardapio_link, "cardapio")
            else:
                empresa.cardapio_link = data.cardapio_link

        try:
            self.db.commit()
            self.db.refresh(empresa)
            
            # Configura bucket MinIO para a nova empresa
            if empresa.cnpj:
                try:
                    bucket_name = gerar_nome_bucket(empresa.cnpj)
                    if bucket_name:
                        from app.utils.minio_client import client
                        if not client.bucket_exists(bucket_name):
                            client.make_bucket(bucket_name)
                        # Configura permissões públicas
                        configurar_permissoes_bucket(bucket_name)
                except Exception as e:
                    # Log do erro mas não falha a criação da empresa
                    from app.utils.logger import logger
                    logger.warning(f"Falha ao configurar bucket MinIO para empresa {empresa.id}: {e}")
                    
        except IntegrityError as e:
            self.db.rollback()
            # verifica se é duplicidade de cardapio_link
            if 'empresas_cardapio_link_key' in str(e.orig):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cardápio link '{data.cardapio_link}' já existe."
                )
            # outros erros de integridade
            raise HTTPException(status_code=400, detail=str(e.orig))

        return empresa

    # Atualiza empresa
    def update_empresa(self, id: int, data: EmpresaUpdate, logo: UploadFile | None = None):
        empresa = self.get_empresa(id)
        payload = data.model_dump(exclude_unset=True)

        # Atualiza dados da empresa (exceto endereço e cardapio_link)
        update_data = {k: v for k, v in payload.items() if k not in ("cardapio_link", "endereco")}
        for key, value in update_data.items():
            setattr(empresa, key, value)

        # Atualiza endereço_id se fornecido (vincula empresa a endereço existente)
        if payload.get("endereco_id"):
            empresa.endereco_id = payload["endereco_id"]

        # Atualiza dados do endereço se fornecido
        if payload.get("endereco"):
            if payload.get("endereco_id"):
                # Atualiza endereço existente
                endereco_data = EnderecoUpdate(**payload["endereco"])
                self.endereco_service.update_endereco(payload["endereco_id"], endereco_data)
            else:
                # Cria novo endereço e vincula à empresa
                endereco_data = EnderecoCreate(**payload["endereco"])
                novo_endereco = self.endereco_service.create_endereco(endereco_data)
                empresa.endereco_id = novo_endereco.id

        # Atualiza logo
        if logo:
            if empresa.logo:
                remover_arquivo_minio(empresa.logo)
            empresa.logo = upload_file_to_minio(self.db, empresa.id, logo, "logo")

        if "aceita_pedido_automatico" in payload:
            empresa.aceita_pedido_automatico = str(payload["aceita_pedido_automatico"]).lower() == "true"

        # Atualiza cardápio
        cardapio = payload.get("cardapio_link")
        if cardapio:
            if isinstance(cardapio, UploadFile):
                if empresa.cardapio_link:
                    remover_arquivo_minio(empresa.cardapio_link)
                empresa.cardapio_link = upload_file_to_minio(self.db, empresa.id, cardapio, "cardapio")
            elif isinstance(cardapio, str):
                empresa.cardapio_link = cardapio

        self.db.commit()
        self.db.refresh(empresa)
        
        # Verifica e configura bucket MinIO após edição
        if empresa.cnpj:
            try:
                bucket_name = gerar_nome_bucket(empresa.cnpj)
                if bucket_name:
                    from app.utils.minio_client import client
                    # Verifica se bucket existe
                    if not client.bucket_exists(bucket_name):
                        client.make_bucket(bucket_name)
                    
                    # Configura permissões públicas (sempre verifica na edição)
                    configurar_permissoes_bucket(bucket_name)
            except Exception as e:
                # Log do erro mas não falha a edição da empresa
                from app.utils.logger import logger
                logger.warning(f"Falha ao verificar/configurar bucket MinIO para empresa {empresa.id}: {e}")
        
        return empresa

    # ---------- HELPER: CONTAGEM DE VÍNCULOS QUE BLOQUEIAM A REMOÇÃO ----------
    def _collect_delete_blockers(self, empresa_id: int) -> dict[str, int]:
        """
        Retorna um dicionário com contagens de vínculos relevantes
        que impedem a remoção da empresa.
        Faz COUNT por tabela (não carrega relationships inteiras).
        """
        produtos_qtd = self.db.query(func.count(ProdutoEmpModel.cod_barras))\
            .filter(ProdutoEmpModel.empresa_id == empresa_id).scalar() or 0

        pedidos_qtd = self.db.query(func.count(PedidoDeliveryModel.id))\
            .filter(PedidoDeliveryModel.empresa_id == empresa_id).scalar() or 0

        regioes_qtd = self.db.query(func.count(RegiaoEntregaModel.id))\
            .filter(RegiaoEntregaModel.empresa_id == empresa_id).scalar() or 0

        entregadores_qtd = self.db.query(func.count())\
            .select_from(entregador_empresa)\
            .filter(entregador_empresa.c.empresa_id == empresa_id).scalar() or 0

        usuarios_qtd = self.db.query(func.count())\
            .select_from(usuario_empresa)\
            .filter(usuario_empresa.c.empresa_id == empresa_id).scalar() or 0

        return {
            "produtos_emp": produtos_qtd,
            "pedidos": pedidos_qtd,
            "regioes_entrega": regioes_qtd,
            "entregadores": entregadores_qtd,
            "usuarios": usuarios_qtd,
        }

    # ---------- DELETE COM TODAS AS VERIFICAÇÕES ----------
    def delete_empresa(self, id: int):
        empresa = self.get_empresa(id)

        # 1) Checa vínculos que bloqueiam a remoção
        blockers = self._collect_delete_blockers(id)

        # Se houver qualquer vínculo, bloqueia e retorna uma lista amigável
        itens_bloqueio = []
        if blockers["produtos_emp"] > 0:
            itens_bloqueio.append(f"{blockers['produtos_emp']} produto(s) vinculado(s)")
        if blockers["pedidos"] > 0:
            itens_bloqueio.append(f"{blockers['pedidos']} pedido(s) vinculado(s)")
        if blockers["regioes_entrega"] > 0:
            itens_bloqueio.append(f"{blockers['regioes_entrega']} região(ões) de entrega vinculada(s)")
        if blockers["entregadores"] > 0:
            itens_bloqueio.append(f"{blockers['entregadores']} vínculo(s) com entregadores")
        if blockers["usuarios"] > 0:
            itens_bloqueio.append(f"{blockers['usuarios']} vínculo(s) com usuários")

        if itens_bloqueio:
            detalhes = (
                "Não é possível remover a empresa porque ainda existem relacionamentos vinculados: "
                + "; ".join(itens_bloqueio)
                + ".\n"
                "- Desvincule ou delete os itens acima antes de remover a empresa.\n"
                "Sugestão de ordem: produtos → regiões de entrega → entregadores/usuários → pedidos (ou arquivar) → empresa."
            )
            raise HTTPException(status_code=400, detail=detalhes)

        # 2) Sem vínculos: prossegue com remoção
        try:
            # Remove arquivos (se existirem) antes do DELETE efetivo
            if empresa.logo:
                remover_arquivo_minio(empresa.logo)
                empresa.logo = None
            if empresa.cardapio_link:
                remover_arquivo_minio(empresa.cardapio_link)
                empresa.cardapio_link = None

            endereco_id = empresa.endereco_id

            # Como já garantimos que não existem vínculos em M:N, por segurança
            # limpamos associações (caso o mapeamento esteja carregado).
            # Isso evita lixo em tabela associativa em bancos sem FK ON DELETE CASCADE.
            if empresa.entregadores:
                empresa.entregadores.clear()
            if empresa.usuarios:
                empresa.usuarios.clear()

            # Persiste limpezas prévias
            self.db.flush()

            # Deleta a empresa
            self.repo_emp.delete(empresa)
            self.db.flush()

            # 3) Apaga o endereço 1:1 (é unique=True; ninguém mais usa)
            if endereco_id:
                self.endereco_service.delete_endereco(endereco_id)

            self.db.commit()

        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=f"Falha ao remover empresa: {str(e)}")