-- Migração: Criação de roles e grants básicos para a aplicação Mensura
-- Ajuste os nomes/senhas das roles de LOGIN conforme seu ambiente antes de aplicar.

-- 1) Roles lógicas (sem login) para controle de acesso a objetos
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mensura_app_rw') THEN
        CREATE ROLE mensura_app_rw NOLOGIN;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mensura_app_ro') THEN
        CREATE ROLE mensura_app_ro NOLOGIN;
    END IF;
END $$;

-- 2) Role de login usada pela API (ajuste senha conforme necessidade)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mensura_api') THEN
        CREATE ROLE mensura_api LOGIN PASSWORD '12540150';
    END IF;
END $$;

-- 3) Concede herança da role lógica para a role de login da aplicação
GRANT mensura_app_rw TO mensura_api;

-- 4) Grants por schema/tabelas/seqüências para as roles da aplicação
--    Inclui os schemas usados pela aplicação, conforme inicialização em app/database/init_db.py
DO $$
DECLARE
    s text;
    schemas text[] := ARRAY[
        'public',
        'cadastros',
        'cardapio',
        'catalogo',
        'financeiro',
        'pedidos',
        'notifications',
        'mesas',
        'balcao'
    ];
BEGIN
    FOREACH s IN ARRAY schemas LOOP
        -- Garante que o schema existe (não falha se já existir)
        EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I;', s);

        -- Uso básico do schema
        EXECUTE format('GRANT USAGE ON SCHEMA %I TO mensura_app_rw, mensura_app_ro;', s);

        -- Tabelas atuais
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA %I TO mensura_app_rw;', s);
        EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO mensura_app_ro;', s);

        -- Sequências (para campos SERIAL/BIGSERIAL)
        EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %I TO mensura_app_rw;', s);
        EXECUTE format('GRANT SELECT ON ALL SEQUENCES IN SCHEMA %I TO mensura_app_ro;', s);

        -- Default privileges para objetos futuros
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO mensura_app_rw;',
            s
        );
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT ON TABLES TO mensura_app_ro;',
            s
        );

        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO mensura_app_rw;',
            s
        );
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT ON SEQUENCES TO mensura_app_ro;',
            s
        );
    END LOOP;
END $$;


