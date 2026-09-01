"""Configuração do AdForge Bot — carrega ~/.adforge/.env."""
import os

ADFORGE_HOME = os.path.expanduser("~/.adforge")
ENV_PATH = os.path.join(ADFORGE_HOME, ".env")
BOT_DIR = os.path.join(ADFORGE_HOME, "bot")
BOT_STATE_DIR = os.path.join(ADFORGE_HOME, "bot_state")
REPORTS_DIR = os.path.join(ADFORGE_HOME, "reports")
LOGS_DIR = os.path.join(ADFORGE_HOME, "logs")

BOT_LLM_DAILY_CAP_BRL = 3.0  # cap separado do daily-analyst (R$10/dia)


def load_env(path=ENV_PATH):
    env = {}
    if not os.path.exists(path):
        return env
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                v = v[1:-1]
            env[k.strip()] = v
    return env


def load_config():
    env = load_env(ENV_PATH)
    return {
        "token": env.get("TELEGRAM_BOT_TOKEN", "").strip(),
        "chat_id": env.get("TELEGRAM_CHAT_ID", "").strip(),
        "api_key": env.get("ANTHROPIC_API_KEY", "").strip(),
    }
