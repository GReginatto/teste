
CREATE TABLE IF NOT EXISTS leads (
    id                BIGSERIAL PRIMARY KEY,         
    nome              TEXT         NOT NULL,
    telefone          TEXT         NOT NULL,
    email             TEXT         NOT NULL UNIQUE,
    especialidade     TEXT         NOT NULL,
    principal_desafio TEXT         NOT NULL,
    clickup_task_id   TEXT,                           
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()  
);

CREATE INDEX IF NOT EXISTS idx_leads_especialidade ON leads (especialidade);

CREATE INDEX IF NOT EXISTS idx_leads_clickup_task ON leads (clickup_task_id)
    WHERE clickup_task_id IS NOT NULL;  -- partial index: só indexa linhas com task criada
