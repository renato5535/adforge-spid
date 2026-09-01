"""AdForge Bot — Fase 1 bidirecional.

Long polling sem webhook, sem dependências externas.

Uso:
  python bot.py          # loop de produção (Ctrl+C para parar)
  python bot.py --once   # processa updates pendentes e sai (útil em cron)
"""
import sys
import os
import time

# Garante que ~/.adforge/bot/ está no path para todos os imports relativos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config
from tg import TGClient
import log
import router


def main():
    cfg      = load_config()
    token    = cfg["token"]
    chat_id  = cfg["chat_id"]
    api_key  = cfg["api_key"]

    if not token or not chat_id:
        print("ERRO: TELEGRAM_BOT_TOKEN e/ou TELEGRAM_CHAT_ID não configurados em ~/.adforge/.env")
        sys.exit(1)

    tg       = TGClient(token)
    once     = "--once" in sys.argv
    # No modo --once (scheduler) usa timeout=0 para retornar imediatamente
    poll_timeout = 0 if once else 30

    if not once:
        print("AdForge Bot iniciado. Aguardando mensagens... (Ctrl+C para parar)")

    log.log_decision("bot/start", {"mode": "once" if once else "loop"}, "iniciado")

    while True:
        try:
            updates, err = tg.get_updates(timeout=poll_timeout)
            if err:
                if not once:
                    print("[poll] Erro: %s — aguardando 5s" % err)
                    time.sleep(5)
                break
            for upd in updates:
                try:
                    router.route_update(upd, tg, chat_id, api_key)
                except Exception as e:
                    print("[upd %s] Erro inesperado: %s" % (upd.get("update_id"), e))

            if once:
                break

        except KeyboardInterrupt:
            print("\nBot encerrado pelo usuário.")
            log.log_decision("bot/stop", {}, "KeyboardInterrupt")
            break
        except Exception as e:
            print("[loop] Erro inesperado: %s — aguardando 10s" % e)
            if once:
                break
            time.sleep(10)

    if not once:
        print("Bot parado.")


if __name__ == "__main__":
    main()
