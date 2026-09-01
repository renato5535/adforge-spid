"""Envia uma mensagem de lembrete especifica via Telegram."""
import sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import load_config
from tg import TGClient

def send(message: str):
    cfg = load_config()
    tg  = TGClient(cfg["token"])
    tg.send(cfg["chat_id"], message)
    print("Enviado:", message[:60])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python send_reminder.py '<mensagem>'")
        sys.exit(1)
    send(sys.argv[1])
