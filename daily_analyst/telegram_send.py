"""Entrega via Telegram. Divide em até 3 partes se passar de ~3800 chars/mensagem."""
from common import http_post_json

LIMIT = 3800   # margem sob o teto de 4096 do Telegram
MAX_PARTS = 3


def _split(text, limit=LIMIT, max_parts=MAX_PARTS):
    """Divide preferindo quebras de linha, respeitando o limite por parte."""
    parts = []
    rest = text
    while rest and len(parts) < max_parts:
        if len(rest) <= limit:
            parts.append(rest)
            rest = ""
            break
        corte = rest.rfind("\n", 0, limit)
        if corte <= 0:
            corte = limit
        parts.append(rest[:corte])
        rest = rest[corte:].lstrip("\n")
    if rest:  # estourou max_parts → anexa aviso de truncamento na última
        parts[-1] = parts[-1][: limit - 40] + "\n\n[...] (resumo truncado)"
    return parts


def send(env, text):
    """Envia `text` ao chat configurado. Retorna dict com status e detalhes."""
    token = env.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = env.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN/CHAT_ID ausente", "parts_sent": 0}

    url = "https://api.telegram.org/bot%s/sendMessage" % token
    parts = _split(text)
    sent = 0
    for i, p in enumerate(parts):
        prefix = ("(%d/%d)\n" % (i + 1, len(parts))) if len(parts) > 1 else ""
        resp, err = http_post_json(url, {
            "chat_id": chat,
            "text": prefix + p,
            "disable_web_page_preview": "true",
        })
        if err or not (resp and resp.get("ok")):
            msg = (resp or {}).get("description", err or "erro desconhecido")
            return {"ok": False, "error": msg, "parts_sent": sent, "parts_total": len(parts)}
        sent += 1
    return {"ok": True, "parts_sent": sent, "parts_total": len(parts)}
