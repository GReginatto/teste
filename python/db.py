"""
Camada de banco de dados — BrioLab Desafio 2

Backend selecionado via variável de ambiente DATABASE_BACKEND:
  - "sqlite"   (padrão) → arquivo local briolab_leads.db, zero dependências
  - "supabase" → Supabase via supabase-py (pip install supabase)
  - "postgres" → PostgreSQL direto via psycopg2 (pip install psycopg2-binary)

Todas as funções públicas têm a mesma assinatura independente do backend.
"""

import os
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path

# Carrega .env da raiz do projeto se existir (sem dependência de python-dotenv)
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

log = logging.getLogger(__name__)

BACKEND = os.environ.get("DATABASE_BACKEND", "sqlite").lower()
SQLITE_PATH = os.path.join(os.path.dirname(__file__), "briolab_leads.db")


# ─────────────────────────────────────────────
# BACKEND: SQLITE
# ─────────────────────────────────────────────

def _sqlite_init(conn: sqlite3.Connection) -> None:
    """
    Cria o schema no SQLite. Usa tipos e sintaxe equivalentes ao schema.sql
    (PostgreSQL), com as adaptações necessárias para SQLite.
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id                INTEGER      PRIMARY KEY AUTOINCREMENT,
            nome              TEXT         NOT NULL,
            telefone          TEXT         NOT NULL,
            email             TEXT         NOT NULL UNIQUE,
            especialidade     TEXT         NOT NULL,
            principal_desafio TEXT         NOT NULL,
            clickup_task_id   TEXT,
            created_at        TEXT         NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_leads_especialidade
            ON leads (especialidade);

        CREATE INDEX IF NOT EXISTS idx_leads_clickup_task
            ON leads (clickup_task_id);
    """)
    conn.commit()


def _sqlite_insert_lead(data: dict) -> int:
    with sqlite3.connect(SQLITE_PATH) as conn:
        _sqlite_init(conn)
        cursor = conn.execute(
            """INSERT INTO leads
               (nome, telefone, email, especialidade, principal_desafio, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                data["nome"],
                data["telefone"],
                data["email"],
                data["especialidade"],
                data["principal_desafio"],
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def _sqlite_update_task(lead_id: int, task_id: str) -> None:
    with sqlite3.connect(SQLITE_PATH) as conn:
        conn.execute(
            "UPDATE leads SET clickup_task_id = ? WHERE id = ?", (task_id, lead_id)
        )
        conn.commit()


# ─────────────────────────────────────────────
# BACKEND: SUPABASE
# ─────────────────────────────────────────────
#
# Requer: pip install supabase
# Variáveis de ambiente:
#   SUPABASE_URL  → https://xxxx.supabase.co
#   SUPABASE_KEY  → anon key (ou service role key para operações server-side)
#

def _get_supabase_client():
    try:
        from supabase import create_client
    except ImportError:
        raise RuntimeError(
            "Backend 'supabase' requer o pacote supabase. "
            "Execute: pip install supabase"
        )
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def _supabase_insert_lead(data: dict) -> int:
    client = _get_supabase_client()
    result = (
        client.table("leads")
        .insert({
            "nome":              data["nome"],
            "telefone":          data["telefone"],
            "email":             data["email"],
            "especialidade":     data["especialidade"],
            "principal_desafio": data["principal_desafio"],
        })
        .execute()
    )
    return result.data[0]["id"]


def _supabase_update_task(lead_id: int, task_id: str) -> None:
    client = _get_supabase_client()
    client.table("leads").update({"clickup_task_id": task_id}).eq("id", lead_id).execute()


# ─────────────────────────────────────────────
# BACKEND: POSTGRESQL (psycopg2)
# ─────────────────────────────────────────────
#
# Requer: pip install psycopg2-binary
# Variável de ambiente:
#   DATABASE_URL → postgresql://user:password@host:5432/dbname
#

def _get_pg_conn():
    try:
        import psycopg2
    except ImportError:
        raise RuntimeError(
            "Backend 'postgres' requer psycopg2. "
            "Execute: pip install psycopg2-binary"
        )
    return psycopg2.connect(os.environ["DATABASE_URL"])


def _pg_insert_lead(data: dict) -> int:
    conn = _get_pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO leads (nome, telefone, email, especialidade, principal_desafio)
                   VALUES (%s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    data["nome"],
                    data["telefone"],
                    data["email"],
                    data["especialidade"],
                    data["principal_desafio"],
                ),
            )
            lead_id = cur.fetchone()[0]
        conn.commit()
        return lead_id
    finally:
        conn.close()


def _pg_update_task(lead_id: int, task_id: str) -> None:
    conn = _get_pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE leads SET clickup_task_id = %s WHERE id = %s",
                (task_id, lead_id),
            )
        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────
# INTERFACE PÚBLICA — mesma API para todos os backends
# ─────────────────────────────────────────────

def insert_lead(data: dict) -> int:
    """
    Insere um lead tratado no banco ativo.
    data deve conter: nome, telefone, email, especialidade, principal_desafio.
    Retorna o ID gerado.
    Lança sqlite3.IntegrityError (ou equivalente) em e-mail duplicado.
    """
    log.info(f"[db:{BACKEND}] Inserindo lead: {data['email']}")
    if BACKEND == "sqlite":
        return _sqlite_insert_lead(data)
    if BACKEND == "supabase":
        return _supabase_insert_lead(data)
    if BACKEND == "postgres":
        return _pg_insert_lead(data)
    raise ValueError(f"DATABASE_BACKEND desconhecido: '{BACKEND}'")


def update_task_id(lead_id: int, task_id: str) -> None:
    """Vincula o ID de tarefa do ClickUp ao lead após criação."""
    log.info(f"[db:{BACKEND}] Atualizando task_id={task_id} para lead_id={lead_id}")
    if BACKEND == "sqlite":
        return _sqlite_update_task(lead_id, task_id)
    if BACKEND == "supabase":
        return _supabase_update_task(lead_id, task_id)
    if BACKEND == "postgres":
        return _pg_update_task(lead_id, task_id)
    raise ValueError(f"DATABASE_BACKEND desconhecido: '{BACKEND}'")
