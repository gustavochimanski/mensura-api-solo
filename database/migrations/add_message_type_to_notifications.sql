-- Migração: Adicionar coluna message_type à tabela notifications
-- Data: 2024

-- Verifica se a coluna já existe antes de adicionar
DO $$
BEGIN
    -- Verifica se a coluna message_type não existe
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'notifications' 
        AND table_name = 'notifications'
        AND column_name = 'message_type'
    ) THEN
        -- Cria o enum MessageType se não existir
        CREATE TYPE notifications.messagetype AS ENUM (
            'marketing',
            'utility',
            'transactional',
            'promotional',
            'alert',
            'system',
            'news'
        );
        
        -- Adiciona a coluna message_type com valor padrão 'utility'
        ALTER TABLE notifications.notifications 
        ADD COLUMN message_type notifications.messagetype NOT NULL DEFAULT 'utility';
        
        -- Cria índice para melhor performance em consultas filtradas por tipo
        CREATE INDEX IF NOT EXISTS idx_notifications_message_type 
        ON notifications.notifications(message_type);
        
        RAISE NOTICE 'Coluna message_type adicionada com sucesso à tabela notifications';
    ELSE
        RAISE NOTICE 'Coluna message_type já existe na tabela notifications';
    END IF;
END $$;

-- Comentário na coluna para documentação
COMMENT ON COLUMN notifications.notifications.message_type IS 
'Tipo da mensagem: marketing (promocional), utility (utilitária), transactional (transacional), promotional (promoções), alert (alertas), system (sistema), news (notícias)';

