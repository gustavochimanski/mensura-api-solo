-- Migração: Adicionar colunas data_hora_abertura e data_hora_fechamento à tabela caixas
-- Data: 2024

-- Verifica se a tabela e colunas existem antes de adicionar
DO $$
BEGIN
    -- Verifica se a tabela existe
    IF EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'cadastros' 
        AND table_name = 'caixas'
    ) THEN
        -- Adiciona coluna data_hora_abertura se não existi
        IF NOT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_schema = 'cadastros' 
            AND table_name = 'caixas'
            AND column_name = 'data_hora_abertura'
        ) THEN
            ALTER TABLE cadastros.caixas 
            ADD COLUMN data_hora_abertura TIMESTAMP NULL;
            
            COMMENT ON COLUMN cadastros.caixas.data_hora_abertura IS 
            'Data e hora informada pelo usuário na abertura do caixa (opcional)';
            
            RAISE NOTICE 'Coluna data_hora_abertura adicionada com sucesso à tabela cadastros.caixas';
        ELSE
            RAISE NOTICE 'Coluna data_hora_abertura já existe na tabela cadastros.caixas';
        END IF;
        
        -- Adiciona coluna data_hora_fechamento se não existir
        IF NOT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_schema = 'cadastros' 
            AND table_name = 'caixas'
            AND column_name = 'data_hora_fechamento'
        ) THEN
            ALTER TABLE cadastros.caixas 
            ADD COLUMN data_hora_fechamento TIMESTAMP NULL;
            
            COMMENT ON COLUMN cadastros.caixas.data_hora_fechamento IS 
            'Data e hora informada pelo usuário no fechamento do caixa (opcional)';
            
            RAISE NOTICE 'Coluna data_hora_fechamento adicionada com sucesso à tabela cadastros.caixas';
        ELSE
            RAISE NOTICE 'Coluna data_hora_fechamento já existe na tabela cadastros.caixas';
        END IF;
    ELSE
        RAISE NOTICE 'Tabela cadastros.caixas não existe. As colunas serão criadas quando a tabela for criada pelo SQLAlchemy.';
    END IF;
END $$;

