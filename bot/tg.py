"""Telegram Bot API client — urllib only, sem dependências externas."""
import json
import urllib.request
import urllib.error
import state

_BASE = "https://api.telegram.org/bot{token}/{method}"
_HEADERS = {"Content-Type": "application/json", "User-Agent": "adforge-bot/1.0"}


class TGClient:
    def __init__(self, token):
        self.token = token
        self._offset = state.get_tg_offset()  # retoma do ponto onde parou

    def _call(self, method, payload=None, http_timeout=35):
        url = _BASE.format(token=self.token, method=method)
        body = json.dumps(payload or {}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=http_timeout) as r:
                return json.loads(r.read().decode("utf-8")), None
        except urllib.error.HTTPError as e:
            try:
                b = json.loads(e.read().decode("utf-8"))
            except Exception:
                b = {"description": str(e)}
            return b, "HTTP %s" % e.code
        except Exception as e:
            return None, str(e)

    def get_updates(self, timeout=30):
        """Long polling. Retorna (lista de updates, erro_ou_None)."""
        resp, err = self._call(
            "getUpdates",
            {"offset": self._offset, "timeout": timeout},
            http_timeout=timeout + 5,
        )
        if err or not resp or not resp.get("ok"):
            return [], err or "resposta inválida"
        updates = resp.get("result", [])
        if updates:
            self._offset = updates[-1]["update_id"] + 1
            state.save_tg_offset(self._offset)  # persiste para a próxima execução
        return updates, None

    def send(self, chat_id, text, reply_markup=None, parse_mode="HTML"):
        """Envia mensagem, opcionalmente com inline keyboard."""
        payload = {
            "chat_id": chat_id,
            "text": text[:4096],
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self._call("sendMessage", payload)

    def answer_callback(self, callback_query_id, text=None):
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text[:200]
        return self._call("answerCallbackQuery", payload)

    def edit_markup(self, chat_id, message_id, reply_markup=None):
        """Remove (reply_markup=None) ou atualiza botões de uma mensagem."""
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "reply_markup": reply_markup if reply_markup is not None else {},
        }
        return self._call("editMessageReplyMarkup", payload)

    def edit_text(self, chat_id, message_id, text, parse_mode="HTML"):
        return self._call("editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text[:4096],
            "parse_mode": parse_mode,
        })


def make_buttons(rows):
    """
    rows: lista de listas de {text, callback_data}
    Retorna InlineKeyboardMarkup compatível com Telegram.
    """
    return {
        "inline_keyboard": [
            [{"text": b["text"], "callback_data": b["callback_data"]} for b in row]
            for row in rows
        ]
    }
