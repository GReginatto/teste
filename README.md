# Desafio Técnico — BrioLab

Automação & IA | Junho 2026

---

## Estrutura do repositório

```
/
├── n8n/
│   └── workflow.json          # Workflow N8N exportado (Desafio 1)
└── python/
    ├── main.py                # Script principal (Desafio 2)
    └── requirements.txt
```

---

## Desafio 1 — Orquestração com N8N

### O que foi construído

Workflow com 6 nós em sequência:

| Nó | Tipo | Função |
|----|------|--------|
| Webhook Trigger | `n8n-nodes-base.webhook` | Recebe POST simulando o webhook do ClickUp quando status muda para "aprovado" |
| Extrair Dados da Tarefa | `n8n-nodes-base.code` | Normaliza o payload do ClickUp, lê `custom_fields` por nome (legenda, data de postagem, tipo de conteúdo) |
| Gerar Hashtags com Claude IA | `n8n-nodes-base.httpRequest` | Chama `POST /v1/messages` da Anthropic API com o texto da legenda |
| Processar Resposta da IA | `n8n-nodes-base.code` | Extrai texto da resposta, adiciona `#` onde falta, faz fallback se a IA falhar |
| Salvar no Supabase | `n8n-nodes-base.httpRequest` | Insere registro na tabela `postagens` via REST API do Supabase |
| Notificação | `n8n-nodes-base.httpRequest` | Envia payload compatível com Slack/Discord para URL configurável |

### Como importar e rodar

1. Suba o N8N localmente via Docker:
   ```bash
   docker run -d --name n8n -p 5678:5678 \
     -e N8N_BASIC_AUTH_ACTIVE=false \
     -v n8n_data:/home/node/.n8n \
     n8nio/n8n
   ```
2. Acesse `http://localhost:5678`
3. Menu lateral → **Workflows** → **Import from file** → selecione `n8n/workflow.json`
4. Configure as variáveis de ambiente no N8N (Settings → Environment Variables):

   | Variável | Descrição |
   |----------|-----------|
   | `ANTHROPIC_API_KEY` | Chave da API da Anthropic |
   | `SUPABASE_URL` | URL do projeto Supabase (ex: `https://xxxx.supabase.co`) |
   | `SUPABASE_ANON_KEY` | Anon/public key do Supabase |
   | `NOTIFICATION_WEBHOOK_URL` | URL de webhook para notificações (Slack, Discord, etc.) |

5. Ative o workflow e dispare um teste com este payload:
   ```json
   {
     "task": {
       "id": "task_abc123",
       "name": "Post Instagram - Dr. João",
       "description": "Compartilhe seu conhecimento com autoridade.",
       "status": { "status": "aprovado" },
       "list": { "name": "Cardiologia" },
       "custom_fields": [
         { "name": "Legenda", "value": "Hoje vou falar sobre prevenção cardiovascular. Cuide do seu coração antes que ele precise de cuidados." },
         { "name": "Data de Postagem", "value": "2026-06-15" },
         { "name": "Tipo de Conteúdo", "value": "feed" }
       ]
     }
   }
   ```

### SQL para criar a tabela no Supabase

```sql
CREATE TABLE postagens (
  id             BIGSERIAL PRIMARY KEY,
  task_id        TEXT NOT NULL,
  task_name      TEXT NOT NULL,
  legenda        TEXT,
  hashtags       TEXT,
  full_caption   TEXT,
  tipo_conteudo  TEXT,
  data_postagem  DATE,
  cliente        TEXT,
  status         TEXT DEFAULT 'aprovado',
  ia_model       TEXT,
  ia_tokens_used INTEGER,
  processed_at   TIMESTAMPTZ,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);
```

### O que simulei (sem conta paga)

- **ClickUp Trigger**: substituído por Webhook Manual com payload documentado acima. Em produção, o ClickUp envia esse webhook nativamente quando o status muda.
- **Notificação**: o nó aponta para `NOTIFICATION_WEBHOOK_URL`. Pode ser testado com qualquer endpoint (webhook.site, Slack incoming webhook gratuito, etc).

---

## Desafio 2 — Backend Python

### Arquitetura

| Arquivo | Responsabilidade |
|---------|-----------------|
| `main.py` | Validação, normalização, orquestração do pipeline e ClickUp |
| `db.py` | Camada de banco de dados — troca de backend sem alterar `main.py` |
| `schema.sql` | Schema SQL explícito, compatível com PostgreSQL/Supabase |

### Etapa 1 — Validação
- Verifica campos obrigatórios: `nome`, `telefone`, `email`, `especialidade`, `principal_desafio`
- Coleta **todos** os erros antes de retornar (fail-all, não fail-fast) — evita que o usuário precise submeter o formulário várias vezes
- Formata telefone para `(XX) XXXXX-XXXX` ou `(XX) XXXX-XXXX`, aceitando DDI `+55`, parênteses, traços e espaços em qualquer combinação
- Normaliza e-mail (lowercase + strip) e valida formato com regex

### Etapa 2 — Banco de dados

O backend é selecionado pela variável `DATABASE_BACKEND`:

| Valor | Quando usar | Dependência |
|-------|-------------|-------------|
| `sqlite` (padrão) | Desenvolvimento local, zero setup | nenhuma (stdlib) |
| `supabase` | Produção — igual ao stack da Brio | `pip install supabase` |
| `postgres` | PostgreSQL próprio ou Supabase via connection string | `pip install psycopg2-binary` |

A interface pública de `db.py` (`insert_lead`, `update_task_id`) é idêntica em todos os backends — `main.py` não sabe qual está ativo.

O schema completo da tabela está em `schema.sql` (PostgreSQL/Supabase). Para Supabase, execute o arquivo no SQL Editor do painel.

### Etapa 3 — ClickUp (simulado)
- Monta o payload completo do `POST /api/v2/list/{list_id}/task`
- Imprime com logs estruturados (endpoint, headers, body)
- Retorna `task_id` simulado e vincula ao lead no banco
- Se a criação de tarefa falhar, o lead já salvo **não é cancelado** — resiliência intencional

### Como rodar

```bash
cd python

# (opcional) ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# SQLite local: nenhuma dependência extra necessária
python main.py

# Com Supabase:
# pip install supabase
# set DATABASE_BACKEND=supabase
# set SUPABASE_URL=https://xxxx.supabase.co
# set SUPABASE_KEY=sua_anon_key
# python main.py
```

Para ativar o ClickUp real, defina as variáveis e descomente as 3 linhas indicadas em `main.py`:

```bash
set CLICKUP_API_TOKEN=pk_xxxx
set CLICKUP_LIST_ID=90123456
set CLICKUP_ASSIGNEE_ID=12345678
```

---

## O que faria diferente com mais tempo

### Desafio 1 — N8N
- **Tratamento de erro por nó**: adicionar nós de `Error Trigger` para capturar falhas do Supabase ou da IA e notificar com contexto de qual etapa falhou
- **Retry com backoff**: o nó HTTP Request suporta retry — configuraria 3 tentativas com intervalo crescente para a chamada de IA
- **Idempotência**: verificar se `task_id` já existe no Supabase antes de inserir, evitando duplicatas em caso de reentrega do webhook do ClickUp
- **Fila de processamento**: para volume alto, substituiria o webhook síncrono por uma fila (Redis/BullMQ) para processar de forma assíncrona

### Desafio 2 — Python
- **FastAPI**: transformar o script em uma API REST real com endpoint `POST /leads`, documentação automática via OpenAPI e validação de schema com Pydantic
- **Supabase SDK**: substituir o SQLite pelo cliente oficial do Supabase, mantendo a mesma interface de funções
- **Testes automatizados**: cobertura de unit tests para `_formatar_telefone` e `_normalizar_email`, e testes de integração para o pipeline completo com banco em memória (`:memory:`)
- **Fila assíncrona para o ClickUp**: a criação de tarefa no ClickUp é a etapa mais frágil (API externa). Moveria para uma fila de background (Celery, ARQ) para não bloquear a resposta ao usuário
- **Variável de ambiente para DB_PATH**: facilitar testes e implantação em diferentes ambientes

---

*Desenvolvido como parte do processo seletivo BrioLab — Junho 2026*
