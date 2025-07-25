# models/produto_empresa.py
from sqlalchemy import ( Column, Integer, String, Numeric, Date, TIMESTAMP )
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ProdutoEmpresaModel(Base):
    __tablename__ = "cadprodemp"
    __table_args__ = {"schema": "public"}

    cade_codigo = Column(Integer, primary_key=True, index=True)
    cade_codempresa = Column(String(3))
    cade_setor = Column(String(5))
    cade_setordep = Column(String(5))
    cade_setorbalanca = Column(String(12))
    cade_codclassificacaoe = Column(String(3))
    cade_codclassificacaos = Column(String(3))
    cade_codmva = Column(String(3))
    cade_etiquetas = Column(Integer)
    cade_dtetq = Column(Date)
    cade_cartazes = Column(Integer)
    cade_tecla = Column(Integer)
    cade_tpemb = Column(String(3))
    cade_qemb = Column(Numeric(18, 5))
    cade_nivel = Column(Integer)
    cade_prioridade = Column(Integer)
    cade_espaco = Column(Integer)
    cade_validade = Column(Integer)
    cade_marcado = Column(String(1))
    cade_ativo = Column(String(1))
    cade_bloqueado = Column(String(1))
    cade_prvenda = Column(Numeric(18, 5))
    cade_prvenda1 = Column(Numeric(18, 5))
    cade_prvenda2 = Column(Numeric(18, 5))
    cade_prvenda3 = Column(Numeric(18, 5))
    cade_prvenda4 = Column(Numeric(18, 5))
    cade_prvenda5 = Column(Numeric(18, 5))
    cade_prvendaanterior = Column(Numeric(18, 5))
    cade_prvendapdv = Column(Numeric(18, 5))
    cade_dtprvenda = Column(Date)
    cade_codusuprvenda = Column(String(4))
    cade_prlista = Column(Numeric(18, 5))
    cade_dtoferta = Column(Date)
    cade_prnormal = Column(Numeric(18, 5))
    cade_oferta = Column(String(1))
    cade_pack = Column(String(1))
    cade_estoque1 = Column(Numeric(18, 5))
    cade_estoque2 = Column(Numeric(18, 5))
    cade_estoque3 = Column(Numeric(18, 5))
    cade_estoque4 = Column(Numeric(18, 5))
    cade_estoque5 = Column(Numeric(18, 5))
    cade_estoque6 = Column(Numeric(18, 5))
    cade_estmin = Column(Numeric(18, 5))
    cade_estmax = Column(Numeric(18, 5))
    cade_regulador = Column(Numeric(18, 5))
    cade_qultcompra = Column(Numeric(18, 5))
    cade_dtultcompra = Column(Date)
    cade_codentiultcompra = Column(Integer)
    cade_dtalteracao = Column(Date)
    cade_codusualteracao = Column(String(4))
    cade_comissao = Column(Numeric(18, 5))
    cade_dtcustos = Column(Date)
    cade_dtauditoria = Column(Date)
    cade_protocolocustos = Column(String(16))
    cade_margemcontrib = Column(Numeric(18, 5))
    cade_margemcontribmin = Column(Numeric(18, 5))
    cade_difcusto = Column(Numeric(18, 5))
    cade_perdas = Column(Numeric(18, 5))
    cade_perdascalc = Column(Numeric(18, 5))
    cade_prnota = Column(Numeric(18, 5))
    cade_credcompra = Column(Numeric(18, 5))
    cade_debcompra = Column(Numeric(18, 5))
    cade_ctnota = Column(Numeric(18, 5))
    cade_ctlogistica = Column(Numeric(18, 5))
    cade_ctmedio = Column(Numeric(18, 5))
    cade_ctfiscal = Column(Numeric(18, 5))
    cade_ctoperacao = Column(Numeric(18, 5))
    cade_ctdesembolso = Column(Numeric(18, 5))
    cade_prnotaant = Column(Numeric(18, 5))
    cade_credcompraant = Column(Numeric(18, 5))
    cade_debcompraant = Column(Numeric(18, 5))
    cade_ctnotaant = Column(Numeric(18, 5))
    cade_ctlogisticaant = Column(Numeric(18, 5))
    cade_ctmedioant = Column(Numeric(18, 5))
    cade_ctfiscalant = Column(Numeric(18, 5))
    cade_ctoperacaoant = Column(Numeric(18, 5))
    cade_ctdesembolsoant = Column(Numeric(18, 5))
    cade_codcontrole = Column(Integer)
    cade_codsetor = Column(Integer)
    cade_codruas = Column(Integer)
    cade_codsecao = Column(Integer)
    cade_codmodulo = Column(Integer)
    cade_altura = Column(Numeric(18, 5))
    cade_comprimento = Column(Numeric(18, 5))
    cade_largura = Column(Numeric(18, 5))
    cade_desconto = Column(Numeric(18, 5))
    cade_estoquemincalc = Column(Numeric(18, 5))
    cade_sugprecomincalc = Column(Numeric(18, 5))
    cade_curvacompra = Column(String(1))
    cade_curvavenda = Column(String(1))
    cade_curvalucro = Column(String(1))
    cade_curvacompracat = Column(String(1))
    cade_curvavendacat = Column(String(1))
    cade_curvalucrocat = Column(String(1))
    cade_extra1 = Column(String(20))
    cade_extra2 = Column(String(20))
    cade_extra3 = Column(String(20))
    cade_extra4 = Column(Integer)
    cade_extra5 = Column(Integer)
    cade_extra6 = Column(Integer)
    cade_extra7 = Column(Numeric(18, 5))
    cade_extra8 = Column(Numeric(18, 5))
    cade_extra9 = Column(Numeric(18, 5))
    cade_debvenda = Column(Numeric(18, 5))
    cade_ctvenda = Column(Numeric(18, 5))
    cade_qtdprvenda1 = Column(Numeric(18, 5))
    cade_qtdprvenda2 = Column(Numeric(18, 5))
    cade_qtdprvenda3 = Column(Numeric(18, 5))
    cade_qtdprvenda4 = Column(Numeric(18, 5))
    cade_qtdprvenda5 = Column(Numeric(18, 5))
    cade_dtultvenda = Column(Date)
    cade_tarapdv = Column(Numeric(18, 5))
    cade_idaglutinadorprod = Column(Integer)
    cade_codgrupovendaapp = Column(Integer)
    cade_abatcompra = Column(Numeric(18, 5))
    cade_abatcompraant = Column(Numeric(18, 5))
    cade_codregracashback = Column(String(3))
    cade_prvendaanterior1 = Column(Numeric(18, 5))
    cade_prvendaanterior2 = Column(Numeric(18, 5))
    cade_prvendaanterior3 = Column(Numeric(18, 5))
    cade_prvendaanterior4 = Column(Numeric(18, 5))
    cade_prvendaanterior5 = Column(Numeric(18, 5))
    cade_prnormal1 = Column(Numeric(18, 5))
    cade_prnormal2 = Column(Numeric(18, 5))
    cade_prnormal3 = Column(Numeric(18, 5))
    cade_prnormal4 = Column(Numeric(18, 5))
    cade_prnormal5 = Column(Numeric(18, 5))
    cade_dthoraprvenda = Column(TIMESTAMP)
    cade_classocial = Column(String(2))
    cade_codvisibilidade = Column(String(3))
    cade_descrvisibilidade = Column(String(25))
    cade_codusumarcado = Column(String(4))
    cade_seqvisibilidadegeral = Column(Integer)
    cade_seqvisibilidadeaplicada = Column(Integer)
    cade_dtinicialoferta = Column(Date)
    cade_dtfinaloferta = Column(Date)
    cade_codmeiospgtooferta = Column(String(500))
    cade_dthoraetiqueta = Column(TIMESTAMP)
    cade_attribcte = Column(String(3))
    cade_attribcts = Column(String(3))
    cade_attribdtinicio = Column(Date)
    cade_attribproc = Column(String(1))
    cade_enviadoecommerce = Column(String(1))
    cade_ecid = Column(Integer)
    cade_limitevenda = Column(Integer)
