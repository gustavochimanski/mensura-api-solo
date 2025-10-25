/**
 * Exemplo de como conectar ao WebSocket de notificações no frontend
 * 
 * Este arquivo mostra como implementar a conexão WebSocket no frontend
 * para receber notificações em tempo real quando novos pedidos chegam.
 */

class NotificationWebSocket {
    constructor(userId, empresaId, baseUrl = 'ws://localhost:8000') {
        this.userId = userId;
        this.empresaId = empresaId;
        this.baseUrl = baseUrl;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // 1 segundo
        this.isConnected = false;
        
        // Callbacks para diferentes tipos de notificação
        this.callbacks = {
            onConnect: null,
            onDisconnect: null,
            onNotification: null,
            onError: null
        };
    }
    
    /**
     * Conecta ao WebSocket
     */
    connect() {
        try {
            const wsUrl = `${this.baseUrl}/api/notifications/ws/notifications/${this.userId}?empresa_id=${this.empresaId}`;
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = (event) => {
                console.log('WebSocket conectado:', event);
                this.isConnected = true;
                this.reconnectAttempts = 0;
                
                if (this.callbacks.onConnect) {
                    this.callbacks.onConnect(event);
                }
                
                // Envia mensagem de ping para manter conexão ativa
                this.sendPing();
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('Erro ao processar mensagem:', error);
                }
            };
            
            this.ws.onclose = (event) => {
                console.log('WebSocket desconectado:', event);
                this.isConnected = false;
                
                if (this.callbacks.onDisconnect) {
                    this.callbacks.onDisconnect(event);
                }
                
                // Tenta reconectar automaticamente
                this.attemptReconnect();
            };
            
            this.ws.onerror = (error) => {
                console.error('Erro no WebSocket:', error);
                
                if (this.callbacks.onError) {
                    this.callbacks.onError(error);
                }
            };
            
        } catch (error) {
            console.error('Erro ao conectar WebSocket:', error);
        }
    }
    
    /**
     * Desconecta do WebSocket
     */
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.isConnected = false;
    }
    
    /**
     * Tenta reconectar automaticamente
     */
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Tentativa de reconexão ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectDelay * this.reconnectAttempts);
        } else {
            console.error('Máximo de tentativas de reconexão atingido');
        }
    }
    
    /**
     * Processa mensagens recebidas
     */
    handleMessage(data) {
        console.log('Mensagem recebida:', data);
        
        switch (data.type) {
            case 'connection':
                console.log('Conectado com sucesso:', data.message);
                break;
                
            case 'notification':
                this.handleNotification(data);
                break;
                
            case 'pong':
                console.log('Pong recebido');
                break;
                
            case 'error':
                console.error('Erro do servidor:', data.message);
                break;
                
            default:
                console.log('Tipo de mensagem não reconhecido:', data.type);
        }
    }
    
    /**
     * Processa notificações recebidas
     */
    handleNotification(data) {
        console.log('Nova notificação:', data);
        
        // Chama callback se definido
        if (this.callbacks.onNotification) {
            this.callbacks.onNotification(data);
        }
        
        // Processa diferentes tipos de notificação
        switch (data.notification_type) {
            case 'novo_pedido':
                this.handleNovoPedido(data);
                break;
                
            case 'pedido_aprovado':
                this.handlePedidoAprovado(data);
                break;
                
            case 'pedido_cancelado':
                this.handlePedidoCancelado(data);
                break;
                
            case 'pedido_entregue':
                this.handlePedidoEntregue(data);
                break;
                
            default:
                console.log('Tipo de notificação não reconhecido:', data.notification_type);
        }
    }
    
    /**
     * Processa notificação de novo pedido
     */
    handleNovoPedido(data) {
        console.log('🎉 Novo pedido recebido!', data);
        
        // Exibe notificação visual
        this.showNotification(data.title, data.message, 'success');
        
        // Atualiza contador de pedidos
        this.updatePedidosCounter();
        
        // Atualiza lista de pedidos se estiver na página correta
        if (window.location.pathname.includes('/pedidos')) {
            this.refreshPedidosList();
        }
    }
    
    /**
     * Processa notificação de pedido aprovado
     */
    handlePedidoAprovado(data) {
        console.log('✅ Pedido aprovado!', data);
        this.showNotification(data.title, data.message, 'info');
    }
    
    /**
     * Processa notificação de pedido cancelado
     */
    handlePedidoCancelado(data) {
        console.log('❌ Pedido cancelado!', data);
        this.showNotification(data.title, data.message, 'warning');
    }
    
    /**
     * Processa notificação de pedido entregue
     */
    handlePedidoEntregue(data) {
        console.log('🚚 Pedido entregue!', data);
        this.showNotification(data.title, data.message, 'success');
    }
    
    /**
     * Exibe notificação visual
     */
    showNotification(title, message, type = 'info') {
        // Implementação usando uma biblioteca de notificações
        // Exemplo com toastr ou similar
        if (typeof toastr !== 'undefined') {
            toastr[type](message, title);
        } else {
            // Fallback para alert nativo
            alert(`${title}: ${message}`);
        }
    }
    
    /**
     * Atualiza contador de pedidos
     */
    updatePedidosCounter() {
        const counter = document.getElementById('pedidos-counter');
        if (counter) {
            const current = parseInt(counter.textContent) || 0;
            counter.textContent = current + 1;
            counter.classList.add('pulse'); // Adiciona animação
        }
    }
    
    /**
     * Atualiza lista de pedidos
     */
    refreshPedidosList() {
        // Implementar lógica para atualizar lista de pedidos
        console.log('Atualizando lista de pedidos...');
        // Exemplo: window.location.reload() ou chamada AJAX
    }
    
    /**
     * Envia ping para manter conexão ativa
     */
    sendPing() {
        if (this.isConnected) {
            this.send({
                type: 'ping'
            });
            
            // Agenda próximo ping
            setTimeout(() => this.sendPing(), 30000); // Ping a cada 30 segundos
        }
    }
    
    /**
     * Envia mensagem para o servidor
     */
    send(data) {
        if (this.ws && this.isConnected) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket não conectado');
        }
    }
    
    /**
     * Define callbacks
     */
    onConnect(callback) {
        this.callbacks.onConnect = callback;
    }
    
    onDisconnect(callback) {
        this.callbacks.onDisconnect = callback;
    }
    
    onNotification(callback) {
        this.callbacks.onNotification = callback;
    }
    
    onError(callback) {
        this.callbacks.onError = callback;
    }
}

// Exemplo de uso
document.addEventListener('DOMContentLoaded', function() {
    // Obtém dados do usuário (do localStorage, sessionStorage, ou variáveis globais)
    const userId = 'user_123'; // Substitua pelo ID real do usuário
    const empresaId = 'empresa_456'; // Substitua pelo ID real da empresa
    
    // Cria instância do WebSocket
    const notificationWS = new NotificationWebSocket(userId, empresaId);
    
    // Define callbacks
    notificationWS.onConnect(() => {
        console.log('Conectado ao sistema de notificações');
    });
    
    notificationWS.onDisconnect(() => {
        console.log('Desconectado do sistema de notificações');
    });
    
    notificationWS.onNotification((data) => {
        console.log('Nova notificação recebida:', data);
    });
    
    notificationWS.onError((error) => {
        console.error('Erro na conexão:', error);
    });
    
    // Conecta
    notificationWS.connect();
    
    // Expõe globalmente para uso em outras partes da aplicação
    window.notificationWS = notificationWS;
});

// Exemplo de como chamar o endpoint para notificar novo pedido
async function notificarNovoPedido(pedidoData) {
    try {
        const response = await fetch('/api/notifications/pedidos/novo-pedido', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('token')
            },
            body: JSON.stringify({
                empresa_id: 'empresa_456',
                pedido_id: pedidoData.id,
                cliente_data: pedidoData.cliente,
                itens: pedidoData.itens,
                valor_total: pedidoData.valor_total,
                metadata: {
                    origem: 'frontend',
                    timestamp: new Date().toISOString()
                }
            })
        });
        
        const result = await response.json();
        console.log('Notificação enviada:', result);
        
    } catch (error) {
        console.error('Erro ao enviar notificação:', error);
    }
}
