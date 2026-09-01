"""LLM client para o bot — Anthropic claude-sonnet-4-6, urllib only.

Cap diário: R$3/dia (separado do daily-analyst que usa R$10/dia).
Comandos estruturados (/relatorio, /status etc.) nunca chamam LLM.
LLM só é invocado para: linguagem natural, /explicar e /modificar.
"""
import json
import urllib.request
import urllib.error
import state

MODEL = "claude-sonnet-4-6"
DAILY_CAP_BRL = 3.0
# ~R$0.02 por 1K tokens (input+output combinados) — mesma taxa do recommender.py
_PRICE_PER_1K_BRL = 0.02


class BudgetExceededError(Exception):
    pass


def chat(api_key, messages, system=None, max_tokens=500):
    """
    Chama o Claude. Retorna (texto_str, custo_brl).
    Lança BudgetExceededError se cap diário do bot atingido.
    """
    if not state.bot_budget_ok(DAILY_CAP_BRL):
        spent = state.get_bot_cost_today()
        raise BudgetExceededError(
            "Cap LLM do bot atingido (R$%.2f/R$%.2f hoje). "
            "Comandos estruturados continuam funcionando. LLM retoma amanhã."
            % (spent, DAILY_CAP_BRL)
        )

    payload = {"model": MODEL, "max_tokens": max_tokens, "messages": messages}
    if system:
        payload["system"] = system

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError("Anthropic HTTP %s" % e.code)
    except Exception as e:
        raise RuntimeError("Erro de rede: %s" % e)

    text = "".join(b.get("text", "") for b in data.get("content", []))
    usage = data.get("usage", {})
    toks = (usage.get("input_tokens", 0) + usage.get("output_tokens", 0)) / 1000.0
    cost_brl = toks * _PRICE_PER_1K_BRL

    state.add_bot_cost(cost_brl)
    return text, cost_brl
