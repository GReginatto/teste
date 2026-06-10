-- Schema BrioLab — Formulário de Diagnóstico
-- Compatível com PostgreSQL / Supabase
-- Para SQLite local, veja os comentários inline

-- Tabela de leads capturados pelo formulário de diagnóstico
CREATE TABLE IF NOT EXISTS leads (
    id                BIGSERIAL PRIMARY KEY,          -- SQLite: INTEGER PRIMARY KEY AUTOINCREMENT
    nome              TEXT         NOT NULL,
    telefone          TEXT         NOT NULL,
    email             TEXT         NOT NULL UNIQUE,
    especialidade     TEXT         NOT NULL,
    principal_desafio TEXT         NOT NULL,
    clickup_task_id   TEXT,                           -- preenchido após Etapa 3
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()  -- SQLite: TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Índice para buscas por especialidade (relatórios comerciais)
CREATE INDEX IF NOT EXISTS idx_leads_especialidade ON leads (especialidade);

-- Índice para joins/buscas por task do ClickUp
CREATE INDEX IF NOT EXISTS idx_leads_clickup_task ON leads (clickup_task_id)
    WHERE clickup_task_id IS NOT NULL;  -- partial index: só indexa linhas com task criada
