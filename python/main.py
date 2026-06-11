"""
Desafio 2 - BrioLab: Backend Python para Formulário de Diagnóstico

Pipeline:
  1. Receber JSON → validar campos obrigatórios, formatar telefone, normalizar e-mail
  2. Persistir dados tratados no banco (SQLite local por padrão; Supabase/PostgreSQL via env)
  3. Criar tarefa no ClickUp via API (simulado com payload documentado)

Banco de dados:
  Controlado por DATABASE_BACKEND (veja db.py).
  Padrão: sqlite — zero dependências externas para rodar localmente.
"""

import json
import re
import os
import logging
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path

# Carrega .env da raiz do projeto se existir
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# ETAPA 1 — VALIDAÇÃO E NORMALIZAÇÃO
# ─────────────────────────────────────────────

@dataclass
class LeadData:
    nome: str
    telefone: str
    email: str
    especialidade: str
    principal_desafio: str
    telefone_fmt: str = field(default="", init=False)
    email_norm: str = field(default="", init=False)


class ValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _formatar_telefone(raw: str) -> str:
    """
    Aceita qualquer formato (com/sem DDI, parênteses, traços, espaços).
    Retorna (XX) XXXXX-XXXX (celular) ou (XX) XXXX-XXXX (fixo).
    """
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    raise ValueError(f"Telefone invalido: '{raw}' -- esperado 10 ou 11 digitos sem DDI")


def _normalizar_email(raw: str) -> str:
    """Lowercase + strip. Valida formato com regex."""
    normalized = raw.strip().lower()
    if not re.match(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$", normalized):
        raise ValueError(f"E-mail invalido: '{raw}'")
    return normalized


def validar(raw: dict) -> LeadData:
    """
    Valida todos os campos antes de retornar erro (fail-all, nao fail-fast).
    Evita que o usuario precise submeter o formulario multiplas vezes.
    """
    erros: list[str] = []
    for campo in ["nome", "telefone", "email", "especialidade", "principal_desafio"]:
        if not str(raw.get(campo, "")).strip():
            erros.append(f"Campo obrigatorio ausente ou vazio: '{campo}'")

    if erros:
        raise ValidationError(erros)

    telefone_fmt = email_norm = ""

    try:
        telefone_fmt = _formatar_telefone(raw["telefone"])
    except ValueError as e:
        erros.append(str(e))

    try:
        email_norm = _normalizar_email(raw["email"])
    except ValueError as e:
        erros.append(str(e))

    if erros:
        raise ValidationError(erros)

    lead = LeadData(
        nome=raw["nome"].strip().title(),
        telefone=raw["telefone"],
        email=raw["email"],
        especialidade=raw["especialidade"].strip(),
        principal_desafio=raw["principal_desafio"].strip(),
    )
    lead.telefone_fmt = telefone_fmt
    lead.email_norm = email_norm
    return lead


# ─────────────────────────────────────────────
# ETAPA 3 — INTEGRAÇÃO COM CLICKUP
# ─────────────────────────────────────────────
#
# DECISÃO: A API do ClickUp requer Bearer Token e IDs de lista específicos de
# cada workspace. Como este desafio não inclui credenciais reais, a chamada é
# simulada: o payload completo é impresso e documentado.
#
# Para ativar em produção:
#   1. pip install requests
#   2. Defina as variáveis de ambiente abaixo
#   3. Descomente o bloco requests.post() no final da função
#

CLICKUP_API      = "https://api.clickup.com/api/v2/list/{list_id}/task"
CLICKUP_LIST_ID  = os.environ.get("CLICKUP_LIST_ID", "SEU_LIST_ID")
CLICKUP_TOKEN    = os.environ.get("CLICKUP_API_TOKEN", "SEU_TOKEN")
CLICKUP_ASSIGNEE = os.environ.get("CLICKUP_ASSIGNEE_ID", "12345678")


def criar_tarefa_clickup(lead: LeadData, lead_id: int) -> str:
    payload = {
        "name": f"[LEAD] {lead.especialidade} - {lead.nome}",
        "description": (
            f"Novo lead via formulario de diagnostico\n\n"
            f"Nome: {lead.nome}\n"
            f"Telefone: {lead.telefone_fmt}\n"
            f"E-mail: {lead.email_norm}\n"
            f"Especialidade: {lead.especialidade}\n\n"
            f"Principal desafio:\n{lead.principal_desafio}\n\n"
            f"Lead ID interno: {lead_id} | "
            f"Capturado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ),
        "assignees": [int(CLICKUP_ASSIGNEE)],
        "status": "to do",
        "priority": 2,  # 1=urgente 2=alta 3=normal 4=baixa
        "custom_fields": [
            {"id": "field_email",     "value": lead.email_norm},
            {"id": "field_phone",     "value": lead.telefone_fmt},
            {"id": "field_specialty", "value": lead.especialidade},
        ],
    }

    endpoint = CLICKUP_API.format(list_id=CLICKUP_LIST_ID)

    log.info("-- SIMULACAO CLICKUP API ------------------------------------------")
    log.info(f"  POST {endpoint}")
    log.info(f"  Headers: Authorization: Bearer [REDACTED]")
    log.info(f"  Body:\n{json.dumps(payload, ensure_ascii=False, indent=4)}")
    log.info("-------------------------------------------------------------------")

    # PRODUCAO: descomente abaixo
    # import requests
    # resp = requests.post(endpoint, json=payload,
    #                      headers={"Authorization": CLICKUP_TOKEN,
    #                               "Content-Type": "application/json"},
    #                      timeout=10)
    # resp.raise_for_status()
    # return resp.json()["id"]

    return f"SIMULATED_{lead_id}_{int(datetime.now().timestamp())}"


# ─────────────────────────────────────────────
# ORQUESTRADOR
# ─────────────────────────────────────────────

def processar_formulario(raw: dict) -> dict:
    log.info("=" * 55)
    log.info("NOVO FORMULARIO RECEBIDO")
    log.info("=" * 55)

    # 1. Validação
    log.info("[1/3] Validando dados...")
    try:
        lead = validar(raw)
        log.info(f"      OK -- {lead.nome} | {lead.telefone_fmt} | {lead.email_norm}")
    except ValidationError as e:
        log.error(f"      FALHA -- {e.errors}")
        return {"ok": False, "etapa": "validacao", "erros": e.errors}

    # 2. Banco de dados
    log.info(f"[2/3] Salvando no banco ({db.BACKEND})...")
    try:
        lead_id = db.insert_lead({
            "nome":              lead.nome,
            "telefone":          lead.telefone_fmt,
            "email":             lead.email_norm,
            "especialidade":     lead.especialidade,
            "principal_desafio": lead.principal_desafio,
        })
        log.info(f"      OK -- ID gerado: {lead_id}")
    except Exception as e:
        msg = str(e)
        if "UNIQUE" in msg.upper() or "unique" in msg.lower() or "duplicate" in msg.lower():
            log.warning("      AVISO -- E-mail duplicado, lead ja cadastrado.")
            return {"ok": False, "etapa": "banco", "erros": ["E-mail ja cadastrado"]}
        log.error(f"      ERRO -- {e}")
        return {"ok": False, "etapa": "banco", "erros": [msg]}

    # 3. ClickUp
    log.info("[3/3] Criando tarefa no ClickUp...")
    task_id = None
    try:
        task_id = criar_tarefa_clickup(lead, lead_id)
        db.update_task_id(lead_id, task_id)
        log.info(f"      OK -- Task ID: {task_id}")
    except Exception as e:
        # Não cancela o fluxo: lead já está salvo; task será criada manualmente se necessário
        log.warning(f"      AVISO -- ClickUp falhou: {e}. Lead {lead_id} salvo sem task_id.")

    return {
        "ok": True,
        "lead_id": lead_id,
        "clickup_task_id": task_id,
        "lead": {
            "nome": lead.nome,
            "telefone": lead.telefone_fmt,
            "email": lead.email_norm,
            "especialidade": lead.especialidade,
        },
    }


# ─────────────────────────────────────────────
# CASOS DE TESTE
# ─────────────────────────────────────────────

CASOS = [
    # ── Casos validos ──────────────────────────────────────────────────────────
    {
        "_desc": "Valido -- cardiologista, com DDI +55 e parenteses",
        "nome": "dr. JOAO SILVA",
        "telefone": "+55 (11) 99988-7766",
        "email": "JOAO.SILVA@GMAIL.COM",
        "especialidade": "Cardiologia",
        "principal_desafio": "Aumentar visibilidade online e atrair pacientes qualificados nas redes sociais",
    },
    {
        "_desc": "Valido -- dentista, celular sem DDI, nome e email em minusculas",
        "nome": "dra. ana lima",
        "telefone": "21987654321",
        "email": "ana.lima@clinicasorriso.com.br",
        "especialidade": "Odontologia",
        "principal_desafio": "Construir autoridade no Instagram e converter seguidores em pacientes de alto ticket",
    },
    {
        "_desc": "Valido -- advogada, telefone com espacos e traco",
        "nome": "BEATRIZ FONTES",
        "telefone": "48 9 9654-3210",
        "email": "beatriz.fontes@escritoriobf.adv.br",
        "especialidade": "Direito Tributario",
        "principal_desafio": "Gerar leads B2B qualificados pelo LinkedIn. Empresas nao me encontram online.",
    },
    {
        "_desc": "Valido -- psicologo, telefone fixo 8 digitos",
        "nome": "renato OLIVEIRA",
        "telefone": "(31) 3322-1100",
        "email": "renato.psi@clinicamente.com.br",
        "especialidade": "Psicologia",
        "principal_desafio": "Desmistificar a terapia online e atrair pacientes que nunca consideraram buscar ajuda",
    },
    {
        "_desc": "Valido -- dermatologista, email com subdominio",
        "nome": "dra. lucia mendes",
        "telefone": "51994321098",
        "email": "dra.lucia@clinicapele.med.br",
        "especialidade": "Dermatologia",
        "principal_desafio": "Posicionar expertise em procedimentos esteticos e diferenciar do concorrente de baixo custo",
    },
    # ── Casos de falha esperada ────────────────────────────────────────────────
    {
        "_desc": "Falha -- multiplos campos obrigatorios ausentes",
        "nome": "Maria",
        "telefone": "",
        "email": "",
        "especialidade": "Advocacia",
        "principal_desafio": "",
    },
    {
        "_desc": "Falha -- telefone com digitos insuficientes",
        "nome": "Dr. Pedro Costa",
        "telefone": "123-456",
        "email": "pedro@escritorio.com",
        "especialidade": "Direito Tributario",
        "principal_desafio": "Gerar leads qualificados pelo LinkedIn",
    },
    {
        "_desc": "Falha -- e-mail malformado (sem dominio)",
        "nome": "Dra. Fernanda Rocha",
        "telefone": "48996543210",
        "email": "fernanda@",
        "especialidade": "Ginecologia",
        "principal_desafio": "Aumentar engajamento no Instagram",
    },
    {
        "_desc": "Falha -- telefone e e-mail invalidos simultaneamente",
        "nome": "Dr. Carlos Menez",
        "telefone": "99",
        "email": "nao-e-um-email",
        "especialidade": "Neurologia",
        "principal_desafio": "Construir presenca digital forte",
    },
]


if __name__ == "__main__":
    for caso in CASOS:
        desc = caso.get("_desc", "")
        dados = {k: v for k, v in caso.items() if k != "_desc"}
        print(f"\n{'=' * 60}")
        print(f"TESTE: {desc}")
        print("=" * 60)
        resultado = processar_formulario(dados)
        print(f"RESULTADO:\n{json.dumps(resultado, ensure_ascii=False, indent=2)}")
