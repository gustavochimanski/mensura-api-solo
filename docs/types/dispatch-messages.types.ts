/**
 * Tipos TypeScript para API de Disparo de Mensagens
 * 
 * Uso:
 * import { DispatchMessageRequest, DispatchMessageResponse } from './types/dispatch-messages.types';
 */

// Tipos de Mensagem
export type MessageType = 
  | 'marketing'
  | 'utility'
  | 'transactional'
  | 'promotional'
  | 'alert'
  | 'system'
  | 'news';

// Canais de Envio
export type NotificationChannel = 
  | 'email'
  | 'whatsapp'
  | 'push'
  | 'webhook'
  | 'in_app'
  | 'sms'
  | 'telegram';

// Prioridades
export type NotificationPriority = 
  | 'low'
  | 'normal'
  | 'high'
  | 'urgent';

// Request para Disparo Individual
export interface DispatchMessageRequest {
  empresa_id: string;
  message_type: MessageType;
  title: string;
  message: string;
  channels: NotificationChannel[];
  user_ids?: string[];
  recipient_emails?: string[];
  recipient_phones?: string[];
  priority?: NotificationPriority;
  event_type?: string;
  event_data?: Record<string, any>;
  channel_metadata?: Record<string, any>;
  scheduled_at?: string; // ISO 8601
}

// Response do Disparo
export interface DispatchMessageResponse {
  success: boolean;
  message_type: MessageType;
  notification_ids: string[];
  total_recipients: number;
  channels_used: NotificationChannel[];
  scheduled: boolean;
  scheduled_at: string | null;
}

// Request para Disparo em Massa
export interface BulkDispatchRequest {
  empresa_id: string;
  message_type: MessageType;
  title: string;
  message: string;
  channels: NotificationChannel[];
  filter_by_empresa: boolean;
  filter_by_user_type?: string;
  filter_by_tags?: string[];
  priority?: NotificationPriority;
  max_recipients?: number;
}

// Estatísticas de Disparo
export interface MessageDispatchStats {
  total: number;
  by_status: Record<string, number>;
  by_channel: Record<string, number>;
  by_message_type: Record<string, number>;
}

// Erro da API
export interface ApiError {
  detail: string;
  status_code?: number;
}

// Constantes úteis
export const MESSAGE_TYPES: Record<string, MessageType> = {
  MARKETING: 'marketing',
  UTILITY: 'utility',
  TRANSACTIONAL: 'transactional',
  PROMOTIONAL: 'promotional',
  ALERT: 'alert',
  SYSTEM: 'system',
  NEWS: 'news'
};

export const CHANNELS: Record<string, NotificationChannel> = {
  EMAIL: 'email',
  WHATSAPP: 'whatsapp',
  PUSH: 'push',
  WEBHOOK: 'webhook',
  IN_APP: 'in_app',
  SMS: 'sms',
  TELEGRAM: 'telegram'
};

export const PRIORITIES: Record<string, NotificationPriority> = {
  LOW: 'low',
  NORMAL: 'normal',
  HIGH: 'high',
  URGENT: 'urgent'
};

// Recomendações de canais por tipo de mensagem
export const RECOMMENDED_CHANNELS: Record<MessageType, NotificationChannel[]> = {
  marketing: ['email', 'push'],
  utility: ['email', 'push'],
  transactional: ['email', 'whatsapp', 'push'],
  promotional: ['email', 'push', 'whatsapp'],
  alert: ['push', 'whatsapp', 'email'],
  system: ['in_app', 'email'],
  news: ['email', 'push']
};

