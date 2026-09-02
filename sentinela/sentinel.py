"""Sentinela AdForge — monitora campanhas Meta a cada 20 minutos.

FASE A (dry-run): loga condições em sentinela/dry_run.log sem enviar Telegram.
FASE B (produção): ativada removendo DRY_RUN=true do .env ou via argumento --live.

Uso:
  python sentinel.py           # dry-run (padrão)
  python sentinel.py --live    # produção (envia Telegram)
"""
import json
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone

SP_TZ = timezone(timedelta(hours=-3))
SENTINEL_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(SENTINEL_DIR, "state.json")
LOG_PATH   = os.path.join(SENTINEL_DIR, "dry_run.log")

# Custo estimado por ciclo (zero LLM na FASE A)
COST_PER_CYCLE_BRL = 0.0


# ── Helpers ────────────────────────────────────────────────────────────────────

def now_sp():
    return datetime.now(SP_TZ)


def now_iso():
    return now_sp().isoformat()


def _load_state():
    today = now_sp().strftime("%Y-%m-%d")
    default = {
        "date": today,
        "llm_calls_today": 0,
        "llm_cost_today_brl": 0.0,
        "conditions": {},
    }
    if not os.path.exists(STATE_PATH):
        return default
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            state = json.load(f)
        # Rotaciona estado se mudou o dia
        if state.get("date") != today:
            state["date"] = today
            state["llm_calls_today"] = 0
            state["llm_cost_today_brl"] = 0.0
            # Mantém conditions (histerese continua entre dias)
        return state
    except Exception:
        return default


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _load_env():
    path = os.path.expanduser("~/.adforge/.env")
    e = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                v = v.strip().strip('"').strip("'")
                e[k.strip()] = v
    except Exception:
        pass
    return e


def _is_silenced():
    """Verifica se o bot está em modo silencioso (arquivo de estado do bot)."""
    silence_path = os.path.expanduser("~/.adforge/bot_state/silenciar.json")
    try:
        with open(silence_path, encoding="utf-8") as f:
            s = json.load(f)
        until_str = s.get("until")
        if not until_str:
            return False
        until = datetime.fromisoformat(until_str)
        return now_sp() < until
    except Exception:
        return False


def _log(msg, log_path=LOG_PATH):
    line = "[%s] %s" % (now_iso(), msg)
    print(line, flush=True)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _check_debounce(state, key, debounce_hours):
    """True se pode alertar (nunca alertou, ou passaram debounce_hours)."""
    cond = state["conditions"].get(key, {})
    last = cond.get("last_alerted")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
        elapsed = (now_sp() - last_dt).total_seconds() / 3600
        return elapsed >= debounce_hours
    except Exception:
        return True


def _mark_alerted(state, key):
    """Registra o timestamp do último alerta."""
    if key in state["conditions"]:
        state["conditions"][key]["last_alerted"] = now_iso()


def _send_telegram(env, text):
    """Envia mensagem Telegram (somente na FASE B)."""
    import urllib.request, urllib.parse
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        _log("ERRO: TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configurados.")
        return False
    url = "https://api.telegram.org/bot%s/sendMessage" % token
    payload = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception as e:
        _log("ERRO Telegram: %s" % e)
        return False


# ── Formatação de alertas ──────────────────────────────────────────────────────

def _format_alert(cond, phase_info):
    t = cond["type"]
    if t == "zero_delivery":
        return (
            "🔴 <b>ZERO DELIVERY</b>\n"
            "Adset: <b>%s</b>\n"
            "Impressões hoje: 0\n"
            "Fase: %s — evento em %d dias"
            % (cond["adset_name"], phase_info["phase"], phase_info["days_until_event"])
        )
    if t == "roas_below_min":
        return (
            "⚠️ <b>ROAS ABAIXO DO MÍNIMO</b>\n"
            "ROAS atual: %.1fx | Mínimo da fase: %.0fx\n"
            "Fase: %s — %s em %d dias"
            % (cond["value"], cond["threshold"],
               phase_info["phase"], phase_info["event_name"],
               phase_info["days_until_event"])
        )
    if t == "overspend":
        return (
            "💸 <b>GASTO ACIMA DO BUDGET</b>\n"
            "Gasto hoje: R$ %.0f | Limite 130%%: R$ %.0f\n"
            "Fase: %s"
            % (cond["value"], cond["threshold"], phase_info["phase"])
        )
    if t == "creative_loss":
        return (
            "📉 <b>QUEDA DE ENTREGA NO CRIATIVO</b>\n"
            "Anúncio: <b>%s</b>\n"
            "Queda: %.0f%% vs ontem\n"
            "Fase: %s"
            % (cond["ad_name"], cond.get("loss_pct", 0) * 100, phase_info["phase"])
        )
    if t == "freq_roas":
        return (
            "🔁 <b>FADIGA DE AUDIÊNCIA</b>\n"
            "Adset: <b>%s</b>\n"
            "Freq 7d: %.1f (limite: %.0f) | ROAS: %.1fx\n"
            "Fase: %s"
            % (cond["adset_name"], cond["frequency"], cond["freq_limit"],
               cond["roas"], phase_info["phase"])
        )
    return "⚠️ Condição desconhecida: %s" % t


# ── Execução principal ─────────────────────────────────────────────────────────

def run(dry_run=True):
    from collectors import collect_metrics
    from evaluators import evaluate_all, DEBOUNCE_HOURS

    _log("=== CICLO INÍCIO (modo=%s) ===" % ("DRY-RUN" if dry_run else "PRODUÇÃO"))

    env = _load_env()
    state = _load_state()

    # Verifica silêncio do bot
    if _is_silenced():
        _log("Bot silenciado. Ciclo abortado.")
        _save_state(state)
        return

    # Coleta métricas
    _log("Coletando métricas da Meta API...")
    try:
        metrics = collect_metrics()
    except Exception as e:
        _log("ERRO fatal na coleta: %s\n%s" % (e, traceback.format_exc()))
        return

    # Reporta erros de coleta (não fatais)
    for err in metrics.get("errors", []):
        _log("  ERRO coleta: %s" % err)

    # Sem campanha ativa → loga e sai (evita ruído)
    if not metrics["has_active_campaign"]:
        _log(
            "Sem campanha ativa (adsets=%d, spend_hoje=R$%.2f). Nenhuma avaliação."
            % (len(metrics["active_adsets"]), metrics["account_today"].get("spend", 0))
        )
        _save_state(state)
        _log("=== CICLO FIM ===")
        return

    # Snapshot de métricas resumidas
    acc_today = metrics["account_today"]
    _log("Conta hoje: spend=R$%.2f, ROAS=%.1fx, imp=%d" % (
        acc_today.get("spend", 0),
        acc_today.get("roas", 0),
        acc_today.get("impressions", 0),
    ))
    _log("Adsets ativos: %d | Budget diário estimado: R$%.0f" % (
        len(metrics["active_adsets"]),
        metrics["daily_budget_total"],
    ))

    # Avalia todas as condições
    conditions, phase_info = evaluate_all(metrics, state)

    _log("Fase: %s | ROAS mín: %.0fx | %s em %d dias" % (
        phase_info["phase"],
        phase_info["roas_min"],
        phase_info["event_name"],
        phase_info["days_until_event"],
    ))

    # Processa cada condição
    triggered_alerts = []
    for cond in conditions:
        _log(
            "  [%s] chave=%s | valor=%s | threshold=%s | consec=%d/%d | ativo=%s | disparado=%s%s"
            % (
                cond["type"],
                cond["key"],
                _fmt_value(cond),
                _fmt_threshold(cond),
                cond.get("consecutive", 0),
                cond.get("required", 0),
                "SIM" if cond.get("active") else "não",
                "SIM" if cond.get("triggered") else "não",
                (" | obs: %s" % cond["note"]) if cond.get("note") else "",
            )
        )

        if not cond.get("triggered"):
            continue

        # Verifica debounce
        can_alert = _check_debounce(state, cond["key"], DEBOUNCE_HOURS.get(cond["type"], 4.0))
        if not can_alert:
            cond_state = state["conditions"].get(cond["key"], {})
            _log("    → Debounce ativo (último alerta: %s). Suprimido." % cond_state.get("last_alerted"))
            continue

        triggered_alerts.append(cond)

    # Dispara alertas
    if not triggered_alerts:
        _log("Nenhum alerta elegível neste ciclo.")
    else:
        _log("%d alerta(s) elegível(is):" % len(triggered_alerts))
        for cond in triggered_alerts:
            msg = _format_alert(cond, phase_info)
            _log("  → ALERTA: %s" % cond["type"])

            if dry_run:
                _log("    [DRY-RUN] Telegram NÃO enviado. Mensagem:\n    %s" % msg.replace("\n", "\n    "))
            else:
                sent = _send_telegram(env, msg)
                if sent:
                    _mark_alerted(state, cond["key"])
                    _log("    Telegram enviado OK.")
                else:
                    _log("    Telegram FALHOU.")

    # Salva estado atualizado
    _save_state(state)
    _log("=== CICLO FIM ===\n")


def _fmt_value(cond):
    t = cond["type"]
    if t in ("zero_delivery", "creative_loss"):
        return "%d imp" % cond.get("value", 0)
    if t == "roas_below_min":
        return "%.2fx" % cond.get("value", 0)
    if t == "overspend":
        return "R$%.0f (%.0f%%)" % (cond.get("value", 0), cond.get("pct", 0) * 100)
    if t == "freq_roas":
        return "freq=%.1f, ROAS=%.1fx" % (cond.get("frequency", 0), cond.get("roas", 0))
    return str(cond.get("value", "?"))


def _fmt_threshold(cond):
    t = cond["type"]
    if t == "roas_below_min":
        return "%.0fx" % cond.get("threshold", 0)
    if t == "overspend":
        return "R$%.0f" % cond.get("threshold", 0)
    if t == "freq_roas":
        return "freq>%.0f + ROAS<3x" % cond.get("freq_limit", 0)
    return str(cond.get("threshold", "?"))


if __name__ == "__main__":
    dry_run = "--live" not in sys.argv
    try:
        run(dry_run=dry_run)
    except Exception as e:
        _log("ERRO não capturado: %s\n%s" % (e, traceback.format_exc()))
        sys.exit(1)
