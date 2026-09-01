"""Log estruturado de decisões do bot.

Arquivo: ~/.adforge/bot/decisions_YYYY-MM.log
Formato: timestamp | comando/callback | payload | resultado
Rotação: novo arquivo por mês (decisions_2026-07.log, decisions_2026-08.log...)
"""
import os
from datetime import datetime, timedelta, timezone

SP_TZ = timezone(timedelta(hours=-3))
_BOT_DIR = os.path.expanduser("~/.adforge/bot")


def _log_path():
    month = datetime.now(SP_TZ).strftime("%Y-%m")
    return os.path.join(_BOT_DIR, "decisions_%s.log" % month)


def log_decision(command_or_callback, payload, resultado):
    """Appenda linha: timestamp | comando | payload | resultado"""
    ts = datetime.now(SP_TZ).strftime("%Y-%m-%dT%H:%M:%S%z")
    # Sanitiza separadores no payload para não quebrar o formato
    payload_str = str(payload).replace("|", "/")
    resultado_str = str(resultado).replace("|", "/")
    line = "%s | %s | %s | %s\n" % (ts, command_or_callback, payload_str, resultado_str)
    path = _log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass  # log nunca deve quebrar o fluxo principal
