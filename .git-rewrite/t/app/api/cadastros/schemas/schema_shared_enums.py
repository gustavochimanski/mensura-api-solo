from enum import Enum

class PedidoStatusEnum(str, Enum):
    P = "P"  # PENDENTE
    I = "I"  # PENDENTE_IMPRESSAO
    R = "R"  # EM_PREPARO
    S = "S"  # SAIU_PARA_ENTREGA
    E = "E"  # ENTREGUE
    C = "C"  # CANCELADO
    D = "D"  # EDITADO
    X = "X"  # EM EDITACAO
    A = "A"  # AGUARDANDO_PAGAMENTO

class TipoEntregaEnum(str, Enum):
    DELIVERY = "DELIVERY"
    RETIRADA = "RETIRADA"

class OrigemPedidoEnum(str, Enum):
    WEB = "WEB"
    APP = "APP"
    BALCAO = "BALCAO"

class PagamentoGatewayEnum(str, Enum):
    MERCADOPAGO = "MERCADOPAGO"
    PAGSEGURO = "PAGSEGURO"
    STRIPE = "STRIPE"
    PIX_INTERNO = "PIX_INTERNO"
    MOCK = "MOCK"
    OUTRO = "OUTRO"

class PagamentoMetodoEnum(str, Enum):
    PIX = "PIX"
    PIX_ONLINE = "PIX_ONLINE"
    CREDITO = "CREDITO"
    DEBITO = "DEBITO"
    DINHEIRO = "DINHEIRO"
    ONLINE = "ONLINE"
    OUTRO = "OUTRO"

class PagamentoStatusEnum(str, Enum):
    PENDENTE = "PENDENTE"
    AUTORIZADO = "AUTORIZADO"
    PAGO = "PAGO"
    RECUSADO = "RECUSADO"
    CANCELADO = "CANCELADO"
    ESTORNADO = "ESTORNADO"
