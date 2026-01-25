# app/api/empresas/services/empresa_service.py
from urllib.parse import parse_qs, urlparse

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile

from app.api.cadastros.models.model_regiao_entrega import RegiaoEntregaModel
from app.api.empresas.models.empresa_model import EmpresaModel
from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.empresas.schemas.schema_empresa import (
    EmpresaCreate,
    EmpresaUpdate,
    EmpresaCardapioLinkResponse,
)
from app.utils.minio_client import upload_file_to_minio, remover_arquivo_minio, gerar_nome_bucket, verificar_e_configurar_permissoes


from app.api.cadastros.models.association_tables import entregador_empresa, usuario_empresa
from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel, TipoEntrega

BASE_LINK_CARDAPIO = "https://chatbot.mensuraapi.com.br"


class EmpresaService:
    def __init__(self, db: Session):
        self.repo_emp = EmpresaRepository(db)
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

    def _gerar_slug_unico(self, slug_base: str, empresa_id_excluir: int | None = None) -> str:
        """
        Gera um slug único verificando se já existe no banco.
        Se existir, adiciona sufixo numérico (ex: campo-magro-2, campo-magro-3, etc.)
        
        Args:
            slug_base: Slug base a ser verificado
            empresa_id_excluir: ID da empresa a ser excluído da verificação (útil na atualização)
        """
        slug = slug_base
        contador = 1
        
        while True:
            empresa_existente = self.repo_emp.get_emp_by_slug(slug)
            # Se não existe ou é a própria empresa sendo atualizada, pode usar
            if not empresa_existente or (empresa_id_excluir and empresa_existente.id == empresa_id_excluir):
                break
            contador += 1
            slug = f"{slug_base}-{contador}"
        
        return slug

    def _gerar_link_cardapio_empresa(self, empresa_id: int) -> str:
        """Gera o link do cardápio apenas com ?empresa=id (sem via=supervisor etc)."""
        return f"{BASE_LINK_CARDAPIO}?empresa={empresa_id}"

    def _normalizar_cardapio_link(self, link: str, empresa_id: int) -> str:
        """
        Normaliza o link do cardápio: apenas ?empresa=id.
        Se o link for do nosso app (mensuraapi) ou contiver 'via=' (ex: via=supervisor),
        retorna BASE?empresa=id. Caso contrário, mantém o link externo como está.
        """
        if not link or not str(link).strip():
            return self._gerar_link_cardapio_empresa(empresa_id)
        link = str(link).strip()
        try:
            parsed = urlparse(link)
            qs = parse_qs(parsed.query)
            # Contém via= (ex: via=supervisor) -> normalizar
            if any(k.lower() == "via" for k in qs):
                return self._gerar_link_cardapio_empresa(empresa_id)
            # Domínio do nosso app (mensuraapi) -> usar apenas ?empresa=id
            if parsed.netloc and "mensuraapi" in parsed.netloc.lower():
                return self._gerar_link_cardapio_empresa(empresa_id)
        except Exception:
            pass
        return link

    # Cria empresa
    def create_empresa(self, data: EmpresaCreate, logo: UploadFile | None = None):
        # Checa se CNPJ já existe
        if data.cnpj and self.repo_emp.get_emp_by_cnpj(data.cnpj):
            raise HTTPException(status_code=400, detail="Empresa já cadastrada (CNPJ)")

        # Garante slug único
        slug = self._gerar_slug_unico(data.slug)

        # Cria empresa
        empresa = EmpresaModel(
            nome=data.nome,
            cnpj=data.cnpj,
            slug=slug,
            timezone=data.timezone or "America/Sao_Paulo",
            horarios_funcionamento=data.horarios_funcionamento,
            cardapio_tema=data.cardapio_tema,
            aceita_pedido_automatico=bool(data.aceita_pedido_automatico),
            redireciona_home=bool(data.redireciona_home),
            redireciona_home_para=data.redireciona_home_para,
            cep=data.cep,
            logradouro=data.logradouro,
            numero=data.numero,
            complemento=data.complemento,
            bairro=data.bairro,
            cidade=data.cidade,
            estado=(data.estado.upper() if data.estado else None),
            ponto_referencia=data.ponto_referencia,
            latitude=data.latitude,
            longitude=data.longitude,
        )
        empresa = self.repo_emp.create(empresa)

        # Upload da logo
        if logo:
            empresa.logo = upload_file_to_minio(self.db, empresa.id, logo, "logo")

        # Link do cardápio: gerar apenas ?empresa=id (sem via=supervisor etc)
        if data.cardapio_link:
            if isinstance(data.cardapio_link, UploadFile):
                empresa.cardapio_link = upload_file_to_minio(self.db, empresa.id, data.cardapio_link, "cardapio")
            else:
                empresa.cardapio_link = self._normalizar_cardapio_link(
                    data.cardapio_link, empresa.id
                )
        else:
            empresa.cardapio_link = self._gerar_link_cardapio_empresa(empresa.id)

        try:
            self.db.commit()
            self.db.refresh(empresa)
            
            # Configura bucket MinIO para a nova empresa
            try:
                # Usa CNPJ se disponível, caso contrário usa slug ou ID como fallback
                identificador_bucket = empresa.cnpj
                if not identificador_bucket:
                    if empresa.slug:
                        identificador_bucket = empresa.slug
                    else:
                        identificador_bucket = f"empresa-{empresa.id}"
                
                bucket_name = gerar_nome_bucket(identificador_bucket)
                if bucket_name:
                    from app.utils.minio_client import get_minio_client
                    client = get_minio_client()
                    if not client.bucket_exists(bucket_name):
                        client.make_bucket(bucket_name)
                    # Verifica e configura permissões públicas
                    verificar_e_configurar_permissoes(bucket_name)
            except Exception as e:
                # Log do erro mas não falha a criação da empresa
                from app.utils.logger import logger
                logger.warning(f"Falha ao configurar bucket MinIO para empresa {empresa.id}: {e}")
                    
        except IntegrityError as e:
            self.db.rollback()
            error_str = str(e.orig)
            # verifica se é duplicidade de cardapio_link
            if 'empresas_cardapio_link_key' in error_str:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cardápio link '{data.cardapio_link}' já existe."
                )
            # verifica se é duplicidade de slug
            if 'empresas_slug_key' in error_str or 'slug' in error_str.lower():
                raise HTTPException(
                    status_code=400,
                    detail=f"Slug '{slug}' já existe. Tente novamente."
                )
            # outros erros de integridade
            raise HTTPException(status_code=400, detail=f"Erro de integridade: {error_str}")

        return empresa

    # Atualiza empresa
    def update_empresa(self, id: int, data: EmpresaUpdate, logo: UploadFile | None = None):
        empresa = self.get_empresa(id)
        payload = data.model_dump(exclude_unset=True)

        # Se slug está sendo atualizado, garante que seja único
        if "slug" in payload and payload["slug"]:
            novo_slug = payload["slug"]
            # Se o slug mudou e já existe (em outra empresa), gera um único
            if novo_slug != empresa.slug:
                payload["slug"] = self._gerar_slug_unico(novo_slug, empresa_id_excluir=id)

        # Atualiza dados da empresa (exceto endereço e cardapio_link)
        update_data = {k: v for k, v in payload.items() if k != "cardapio_link"}
        for key, value in update_data.items():
            if key == "aceita_pedido_automatico" and value is not None:
                empresa.aceita_pedido_automatico = bool(value)
            elif key == "redireciona_home" and value is not None:
                empresa.redireciona_home = bool(value)
            elif key == "redireciona_home_para" and value is not None:
                empresa.redireciona_home_para = value
            elif key == "estado" and value is not None:
                empresa.estado = value.upper()
            elif key == "timezone" and value is not None:
                empresa.timezone = value
            else:
                setattr(empresa, key, value)

        # Atualiza logo
        if logo:
            if empresa.logo:
                remover_arquivo_minio(empresa.logo)
            empresa.logo = upload_file_to_minio(self.db, empresa.id, logo, "logo")

        # Atualiza cardápio: normalizar para apenas ?empresa=id (sem via=supervisor etc)
        cardapio = payload.get("cardapio_link")
        if cardapio:
            if isinstance(cardapio, UploadFile):
                if empresa.cardapio_link:
                    remover_arquivo_minio(empresa.cardapio_link)
                empresa.cardapio_link = upload_file_to_minio(self.db, empresa.id, cardapio, "cardapio")
            elif isinstance(cardapio, str):
                empresa.cardapio_link = self._normalizar_cardapio_link(cardapio, empresa.id)

        try:
            self.db.commit()
            self.db.refresh(empresa)
        except IntegrityError as e:
            self.db.rollback()
            error_str = str(e.orig)
            # verifica se é duplicidade de cardapio_link
            if 'empresas_cardapio_link_key' in error_str:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cardápio link '{payload.get('cardapio_link')}' já existe."
                )
            # verifica se é duplicidade de slug
            if 'empresas_slug_key' in error_str or 'slug' in error_str.lower():
                raise HTTPException(
                    status_code=400,
                    detail=f"Slug '{payload.get('slug')}' já existe. Tente novamente."
                )
            # outros erros de integridade
            raise HTTPException(status_code=400, detail=f"Erro de integridade: {error_str}")
        
        # Verifica e configura bucket MinIO após edição
        try:
            # Usa CNPJ se disponível, caso contrário usa slug ou ID como fallback
            identificador_bucket = empresa.cnpj
            if not identificador_bucket:
                if empresa.slug:
                    identificador_bucket = empresa.slug
                else:
                    identificador_bucket = f"empresa-{empresa.id}"
            
            bucket_name = gerar_nome_bucket(identificador_bucket)
            if bucket_name:
                from app.utils.minio_client import get_minio_client
                client = get_minio_client()
                # Verifica se bucket existe
                if not client.bucket_exists(bucket_name):
                    client.make_bucket(bucket_name)
                
                # Verifica e configura permissões públicas (sempre verifica na edição)
                verificar_e_configurar_permissoes(bucket_name)
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

        pedidos_qtd = self.db.query(func.count(PedidoUnificadoModel.id))\
            .filter(PedidoUnificadoModel.empresa_id == empresa_id).scalar() or 0

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
                + "- Desvincule ou delete os itens acima antes de remover a empresa.\n"
                + "Sugestão de ordem: produtos → regiões de entrega → entregadores/usuários → pedidos (ou arquivar) → empresa."
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

            self.db.commit()

        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=f"Falha ao remover empresa: {str(e)}")

