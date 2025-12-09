/**
 * Serviço de Disparo de Mensagens
 * 
 * Exemplo de implementação de um serviço para disparo de mensagens
 */

import {
  DispatchMessageRequest,
  DispatchMessageResponse,
  BulkDispatchRequest,
  MessageDispatchStats,
  ApiError
} from '../types/dispatch-messages.types';

class DispatchMessageService {
  private baseUrl: string;
  private getToken: () => string | null;

  constructor(baseUrl: string = '/api/notifications/messages', getToken: () => string | null = () => localStorage.getItem('token')) {
    this.baseUrl = baseUrl;
    this.getToken = getToken;
  }

  /**
   * Dispara uma mensagem individual
   */
  async dispatchMessage(request: DispatchMessageRequest): Promise<DispatchMessageResponse> {
    const response = await fetch(`${this.baseUrl}/dispatch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getToken()}`
      },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.detail || `Erro ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Dispara mensagem em massa
   */
  async bulkDispatch(request: BulkDispatchRequest): Promise<DispatchMessageResponse> {
    const response = await fetch(`${this.baseUrl}/bulk-dispatch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getToken()}`
      },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.detail || `Erro ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Obtém estatísticas de disparo
   */
  async getStats(
    empresaId: string,
    options?: {
      messageType?: string;
      startDate?: string;
      endDate?: string;
    }
  ): Promise<MessageDispatchStats> {
    const params = new URLSearchParams({ empresa_id: empresaId });
    
    if (options?.messageType) {
      params.append('message_type', options.messageType);
    }
    if (options?.startDate) {
      params.append('start_date', options.startDate);
    }
    if (options?.endDate) {
      params.append('end_date', options.endDate);
    }

    const response = await fetch(`${this.baseUrl}/stats?${params.toString()}`, {
      headers: {
        'Authorization': `Bearer ${this.getToken()}`
      }
    });

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.detail || `Erro ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Valida request antes de enviar
   */
  validateRequest(request: DispatchMessageRequest): string[] {
    const errors: string[] = [];

    if (!request.empresa_id) {
      errors.push('empresa_id é obrigatório');
    }

    if (!request.title || request.title.trim().length === 0) {
      errors.push('title é obrigatório');
    }

    if (!request.message || request.message.trim().length === 0) {
      errors.push('message é obrigatória');
    }

    if (!request.channels || request.channels.length === 0) {
      errors.push('Pelo menos um canal deve ser especificado');
    }

    const hasRecipients = 
      (request.user_ids && request.user_ids.length > 0) ||
      (request.recipient_emails && request.recipient_emails.length > 0) ||
      (request.recipient_phones && request.recipient_phones.length > 0);

    if (!hasRecipients) {
      errors.push('Pelo menos um destinatário deve ser fornecido (user_ids, recipient_emails ou recipient_phones)');
    }

    return errors;
  }
}

// Exportar instância singleton
export const dispatchService = new DispatchMessageService();

// Exportar classe para uso customizado
export default DispatchMessageService;

