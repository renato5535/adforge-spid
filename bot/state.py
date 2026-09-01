"""Estado persistente do bot em ~/.adforge/bot_state/.

Arquivos:
  pending_approvals.json  — aprovações com botões aguardando resposta
  silenciar.json          — pausa de notificações com timestamp de expiração
  last_decision.json      — última decisão (para /desfazer_ultima)
  bot_llm_cost.json       — custo LLM diário do bot (cap R$3/dia, separado do daily-analyst)
"""
import os
import json
from datetime import datetime, timedelta, timezone

SP_TZ = timezone(timedelta(hours=-3))

_STATE_DIR = os.path.expanduser("~/.adforge/bot_state")
_APPROVALS = os.path.join(_STATE_DIR, "pending_approvals.json")
_SILENCIAR = os.path.join(_STATE_DIR, "silenciar.json")
_LAST_DEC  = os.path.join(_STATE_DIR, "last_decision.json")
_BOT_COST  = os.path.join(_STATE_DIR, "bot_llm_cost.json")
_OR_COST   = os.path.join(_STATE_DIR, "or_llm_cost.json")


def _ensure():
    os.makedirs(_STATE_DIR, exist_ok=True)


def _read(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {} if default is None else default


def _write(path, data):
    _ensure()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Pending approvals ─────────────────────────────────────────────────────────

def add_pending(rec_id, data):
    approvals = _read(_APPROVALS)
    approvals[rec_id] = data
    _write(_APPROVALS, approvals)


def get_pending(rec_id):
    return _read(_APPROVALS).get(rec_id)


def remove_pending(rec_id):
    approvals = _read(_APPROVALS)
    removed = approvals.pop(rec_id, None)
    _write(_APPROVALS, approvals)
    return removed


def list_pending():
    return _read(_APPROVALS)


# ── Silenciar notificações ────────────────────────────────────────────────────

def set_silenciar(hours):
    until = datetime.now(SP_TZ) + timedelta(hours=hours)
    _write(_SILENCIAR, {"until": until.isoformat()})


def clear_silenciar():
    _write(_SILENCIAR, {})


def is_silenced():
    data = _read(_SILENCIAR)
    until_str = data.get("until")
    if not until_str:
        return False
    try:
        until = datetime.fromisoformat(until_str)
        return datetime.now(SP_TZ) < until
    except Exception:
        return False


def silenced_until_str():
    return _read(_SILENCIAR).get("until", "")


# ── Última decisão (para /desfazer_ultima) ───────────────────────────────────

def set_last_decision(data):
    _write(_LAST_DEC, data)


def get_last_decision():
    return _read(_LAST_DEC)


def clear_last_decision():
    _write(_LAST_DEC, {})


# ── Custo LLM diário do bot (cap R$3/dia) ────────────────────────────────────

def get_bot_cost_today():
    today = datetime.now(SP_TZ).strftime("%Y-%m-%d")
    return float(_read(_BOT_COST).get(today, 0.0))


def add_bot_cost(amount_brl):
    today = datetime.now(SP_TZ).strftime("%Y-%m-%d")
    data = _read(_BOT_COST)
    data[today] = float(data.get(today, 0.0)) + float(amount_brl)
    # Mantém apenas os últimos 7 dias
    for d in sorted(data.keys(), reverse=True)[7:]:
        del data[d]
    _write(_BOT_COST, data)


def bot_budget_ok(daily_limit_brl=3.0):
    return get_bot_cost_today() < daily_limit_brl


# ── Custo OpenRouter diário (cap R$5/dia) ────────────────────────────────────

def get_or_cost_today():
    today = datetime.now(SP_TZ).strftime("%Y-%m-%d")
    return float(_read(_OR_COST).get(today, 0.0))


def add_or_cost(amount_brl):
    today = datetime.now(SP_TZ).strftime("%Y-%m-%d")
    data = _read(_OR_COST)
    data[today] = float(data.get(today, 0.0)) + float(amount_brl)
    for d in sorted(data.keys(), reverse=True)[7:]:
        del data[d]
    _write(_OR_COST, data)


# ── Histórico de conversa por chat_id (memória de sessão) ────────────────────

_HISTORY = os.path.join(_STATE_DIR, "chat_history.json")
_HISTORY_MAX = 10  # mensagens (pares user+assistant)


def get_history(chat_id):
    """Retorna lista de mensagens {role, content} para o chat_id."""
    return _read(_HISTORY, default={}).get(str(chat_id), [])


def add_to_history(chat_id, role, content):
    """Adiciona mensagem ao histórico, mantendo janela de _HISTORY_MAX pares."""
    data = _read(_HISTORY, default={})
    key  = str(chat_id)
    msgs = data.get(key, [])
    msgs.append({"role": role, "content": content[:2000]})  # trunca mensagens longas
    # Mantém no máximo _HISTORY_MAX * 2 entradas (user + assistant por par)
    if len(msgs) > _HISTORY_MAX * 2:
        msgs = msgs[-((_HISTORY_MAX * 2)):]
    data[key] = msgs
    _write(_HISTORY, data)


def clear_history(chat_id):
    data = _read(_HISTORY, default={})
    data.pop(str(chat_id), None)
    _write(_HISTORY, data)


# ── Offset do Telegram (persistido entre execuções --once) ────────────────────

_TG_OFFSET = os.path.join(_STATE_DIR, "tg_offset.json")


def get_tg_offset():
    """Retorna o último offset salvo (0 se nunca salvo)."""
    return int(_read(_TG_OFFSET, default={}).get("offset", 0))


def save_tg_offset(offset):
    """Persiste o offset para que a próxima execução não re-processe updates."""
    _write(_TG_OFFSET, {"offset": offset})
