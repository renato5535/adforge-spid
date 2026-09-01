"""Cliente OpenRouter para geração de variações de copy criativo.

Separado do llm.py (Anthropic direto) para manter caps independentes.
Modelo padrão: openai/gpt-4o-mini (barato, rápido, bom para copy).
"""
import json
import urllib.request
import urllib.error
import os
import sys

# Garante acesso ao state
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state

MODEL    = "meta-llama/llama-3.1-70b-instruct"
CAP_BRL  = 5.0          # cap diário separado para OpenRouter
# llama-3.1-70b: ~$0.10/1M input + $0.28/1M output → ~R$0.002 por 1K tokens
_PRICE_PER_1K_BRL = 0.002

# System prompt de copy para SPID Cup
_COPY_SYSTEM = """Você é um copywriter especialista em eventos de arrancada brasileira, trabalhando para o SPID Cup (São Paulo International Dragway, Itatiba/SP).

REGRAS ABSOLUTAS:
- Nunca use métricas sem confirmação: X categorias, Y carros, Z público — PROIBIDO inventar.
- Dados fixos permitidos: 201m de pista, Pro Mod a 355 km/h, 28 a 30/Ago/2026, Itatiba/SP.
- "201m de pista" NÃO entra em copy emocional — é dado técnico sem impacto no público geral.
- Dado só entra em copy se criar sensação imediata (355 km/h cria, 201m não cria).
- Português brasileiro natural. Frases curtas. Sem formalidade de IA.
- Proibido: "experiência imersiva", "adrenalina pura", "evento imperdível", "diversão garantida".
- Proibido: "paddock", "grid", "pole position", "volta rápida", "racha".
- Correto: "boxes", "pinheirinho", "arrancada", "pista", "drag".
- SPID Cup NÃO é festival. Usar: evento, etapa, arrancada.
- Emojis: máximo 3 por texto.

PREÇOS ATUAIS (3ª Etapa SPID Cup 2026):
- Individual: R$80 (2º lote)
- Família (2 pessoas): R$135 (3º lote)
- Passaporte (3 dias individual): R$120 (1º lote)
- Sexta-feira: R$40 (meia-entrada)

FORMATO DE SAÍDA (sempre exatamente assim):
BODY 1: [até 125 caracteres — hook + benefício]
BODY 2: [até 125 caracteres — ângulo diferente]
BODY 3: [até 125 caracteres — urgência ou preço]

HEADLINE 1: [até 40 caracteres]
HEADLINE 2: [até 40 caracteres]
HEADLINE 3: [até 40 caracteres]"""


class BudgetExceededError(Exception):
    pass


def gerar_variacao(or_key, briefing, max_tokens=600):
    """
    Gera bodies + headlines para Meta Ads via OpenRouter.
    Retorna (texto_formatado, custo_brl).
    """
    spent = state.get_or_cost_today()
    if spent >= CAP_BRL:
        raise BudgetExceededError(
            "Cap OpenRouter atingido (R$%.2f/R$%.2f hoje). Retoma amanhã." % (spent, CAP_BRL)
        )

    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": _COPY_SYSTEM},
            {"role": "user", "content": (
                "Crie variações de copy para Meta Ads com base neste briefing:\n\n"
                "%s\n\n"
                "OBRIGATÓRIO: use exatamente o formato abaixo, sem texto extra:\n\n"
                "BODY 1: [texto]\n"
                "BODY 2: [texto]\n"
                "BODY 3: [texto]\n\n"
                "HEADLINE 1: [texto]\n"
                "HEADLINE 2: [texto]\n"
                "HEADLINE 3: [texto]"
            ) % briefing},
        ],
    }

    body = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": "Bearer %s" % or_key,
            "Content-Type":  "application/json",
            "HTTP-Referer":  "https://adforge.spidcup",
            "X-Title":       "AdForge SPID Cup",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError("OpenRouter HTTP %s: %s" % (e.code, e.read().decode("utf-8","replace")[:200]))
    except Exception as e:
        raise RuntimeError("Erro de rede: %s" % e)

    text  = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})
    toks  = (usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)) / 1000.0
    cost  = toks * _PRICE_PER_1K_BRL

    state.add_or_cost(cost)
    return text.strip(), cost
