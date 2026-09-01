"""Utilidades compartilhadas do daily-analyst.

Sem dependências externas (apenas stdlib) para rodar unattended via Task Scheduler.
"""
import os
import json
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

ADFORGE_HOME = os.path.expanduser("~/.adforge")
ENV_PATH = os.path.join(ADFORGE_HOME, ".env")
REPORTS_DIR = os.path.join(ADFORGE_HOME, "reports")
SHOTS_DIR = os.path.join(REPORTS_DIR, "screenshots")
LOGS_DIR = os.path.join(ADFORGE_HOME, "logs")
CONTEXT_DIR = os.path.join(ADFORGE_HOME, "context")

# São Paulo não tem horário de verão desde 2019 → UTC-3 fixo (sem dependência de tzdata).
SP_TZ = timezone(timedelta(hours=-3))


_CONTEXT_FILES = [
    "benchmarks_spid.md",
    "metas_2026_etapa03.md",
    "estrutura_campanha.md",
    "glossario_arrancada.md",
    "historico_criativos.md",
    "politicas_criativas.md",
    "otimizacoes_recentes.md",
]


def load_context_files():
    """Lê os reference files de ~/.adforge/context/; retorna dict nome->conteúdo.
    Falhas silenciosas — ausência de arquivo não quebra o pipeline."""
    ctx = {}
    for fname in _CONTEXT_FILES:
        path = os.path.join(CONTEXT_DIR, fname)
        try:
            with open(path, encoding="utf-8") as fh:
                ctx[fname] = fh.read()
        except Exception:
            ctx[fname] = ""
    return ctx


def load_env(path=ENV_PATH):
    """Lê o .env (formato KEY=VALUE), removendo aspas simples/duplas dos valores."""
    env = {}
    if not os.path.exists(path):
        return env
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                v = v[1:-1]
            env[k.strip()] = v
    return env


def ad_account(env):
    """Normaliza o ID da conta — o valor no .env já vem com prefixo act_."""
    acc = (env.get("META_AD_ACCOUNT_ID") or "").strip()
    return acc if acc.startswith("act_") else "act_" + acc


def now_sp():
    return datetime.now(SP_TZ)


def http_get_json(url, params=None, timeout=40):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "adforge-daily-analyst/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            body = {"error": {"message": str(e)}}
        return body, "HTTP %s" % e.code
    except Exception as e:
        return None, str(e)


def http_post_json(url, data, timeout=40):
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"User-Agent": "adforge-daily-analyst/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        try:
            b = json.loads(e.read().decode("utf-8"))
        except Exception:
            b = {"error": {"message": str(e)}}
        return b, "HTTP %s" % e.code
    except Exception as e:
        return None, str(e)


def f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def brl(v):
    """Formata em Real brasileiro: 1234.5 -> 'R$ 1.234,50'."""
    s = "%0.2f" % f(v)
    inteiro, dec = s.split(".")
    neg = inteiro.startswith("-")
    inteiro = inteiro.lstrip("-")
    grupos = []
    while len(inteiro) > 3:
        grupos.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    grupos.insert(0, inteiro)
    return ("R$ -" if neg else "R$ ") + ".".join(grupos) + "," + dec


def pct(novo, velho):
    """Variação percentual velho->novo. Retorna None se base zero."""
    velho = f(velho)
    if velho == 0:
        return None
    return (f(novo) - velho) / velho * 100.0


def pct_str(p):
    if p is None:
        return "n/d"
    return ("+%.0f%%" % p) if p >= 0 else ("%.0f%%" % p)
