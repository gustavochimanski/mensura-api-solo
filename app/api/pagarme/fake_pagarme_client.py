import threading
import time
from uuid import uuid4

import requests

class FakePagarmeClient:
    def criar_transacao(self, pedido, metodo_pagamento, token_cartao=None):
        transacao_id = str(uuid4())
        pedido_id = pedido.id

        # Simula envio de webhook em segundo plano
        threading.Thread(
            target=self.enviar_webhook_simulado,
            args=(pedido_id, transacao_id),
            daemon=True
        ).start()

        return {
            "status": "processing",  # Status inicial (simulando "em análise")
            "transaction_id": transacao_id,
            "boleto_url": "https://fake.boleto" if metodo_pagamento == "boleto" else None,
            "pix_qr_code_url": "https://fake.qr.pix" if metodo_pagamento == "pix" else None
        }

    def enviar_webhook_simulado(self, pedido_id, transacao_id):
        time.sleep(20)  # espera 20 segundos
        payload = {
            "event": "transaction_status_changed",
            "transaction": {
                "id": transacao_id,
                "status": "paid",
                "metadata": {"pedido_id": pedido_id}
            }
        }

        try:
            print(f"[WEBHOOK] Enviando webhook simulado para pedido {pedido_id}")
            requests.post("http://localhost:8000/pagamentos/webhook", json=payload)
        except Exception as e:
            print(f"[WEBHOOK] Erro ao enviar webhook simulado: {e}")
