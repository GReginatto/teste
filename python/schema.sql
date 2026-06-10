-- Schema BrioLab — compatível com PostgreSQL e Supabase
-- Execute no SQL Editor do Supabase antes de rodar qualquer integração

-- ─────────────────────────────────────────────
-- Desafio 2: leads do formulário de diagnóstico
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS leads (
    id                BIGSERIAL    PRIMARY KEY,
    nome              TEXT         NOT NULL,
    telefone          TEXT         NOT NULL,
    email             TEXT         NOT NULL UNIQUE,
    especialidade     TEXT         NOT NULL,
    principal_desafio TEXT         NOT NULL,
    clickup_task_id   TEXT,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_especialidade
    ON leads (especialidade);

CREATE INDEX IF NOT EXISTS idx_leads_clickup_task
    ON leads (clickup_task_id)
    WHERE clickup_task_id IS NOT NULL;

-- ─────────────────────────────────────────────
-- Desafio 1: postagens processadas pelo N8N
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS postagens (
    id              BIGSERIAL    PRIMARY KEY,
    task_id         TEXT         NOT NULL,
    task_name       TEXT         NOT NULL,
    legenda         TEXT,
    hashtags        TEXT,
    full_caption    TEXT,
    tipo_conteudo   TEXT,
    data_postagem   DATE,
    cliente         TEXT,
    status          TEXT         DEFAULT 'aprovado',
    ia_model        TEXT,
    ia_tokens_used  INTEGER,
    processed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_postagens_task_id
    ON postagens (task_id);

CREATE INDEX IF NOT EXISTS idx_postagens_cliente
    ON postagens (cliente);

-- ─────────────────────────────────────────────
-- RLS: desabilitado para inserções via anon key
-- Em produção: usar service_role key server-side
-- ou criar policies específicas por operação
-- ─────────────────────────────────────────────

ALTER TABLE leads     DISABLE ROW LEVEL SECURITY;
ALTER TABLE postagens DISABLE ROW LEVEL SECURITY;
