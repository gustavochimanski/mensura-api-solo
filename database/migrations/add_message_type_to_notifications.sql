-- Migração: Adicionar coluna message_type à tabela notifications
-- Data: 2024

-- Garante que o schema notifications existe
CREATE SCHEMA IF NOT EXISTS notifications;

-- Verifica se a tabela e coluna existem antes de adicionar
DO $$
BEGIN
    -- Primeiro, verifica se a tabela existe
    IF EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'notifications' 
        AND table_name = 'notifications'
    ) THEN
        -- Verifica se a coluna message_type não existe
        IF NOT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_schema = 'notifications' 
            AND table_name = 'notifications'
            AND column_name = 'message_type'
        ) THEN
            -- Cria o enum MessageType se não existir
            IF NOT EXISTS (
                SELECT 1 
                FROM pg_type t 
                JOIN pg_namespace n ON n.oid = t.typnamespace 
                WHERE n.nspname = 'notifications' 
                AND t.typname = 'messagetype'
            ) THEN
                CREATE TYPE notifications.messagetype AS ENUM (
                    'marketing',
                    'utility',
                    'transactional',
                    'promotional',
                    'alert',
                    'system',
                    'news'
                );
                RAISE NOTICE 'Tipo enum messagetype criado';
            END IF;
            
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
    ELSE
        RAISE NOTICE 'Tabela notifications.notifications não existe. A coluna será criada quando a tabela for criada pelo SQLAlchemy.';
    END IF;
END $$;

-- Comentário na coluna para documentação (apenas se a tabela existir)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'notifications' 
        AND table_name = 'notifications'
    ) AND EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'notifications' 
        AND table_name = 'notifications'
        AND column_name = 'message_type'
    ) THEN
        COMMENT ON COLUMN notifications.notifications.message_type IS 
        'Tipo da mensagem: marketing (promocional), utility (utilitária), transactional (transacional), promotional (promoções), alert (alertas), system (sistema), news (notícias)';
    END IF;
END $$;

