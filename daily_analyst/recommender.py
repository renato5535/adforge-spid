"""Passo D — Recomendações priorizadas (máx. 5).

HÍBRIDO: gera uma base por regras (sempre) e, se houver API key de LLM no .env e
budget disponível, refina/reescreve as recomendações de forma mais consultiva.
Sem key → retorna as regras (degradação graciosa, custo R$0).

Para ativar a camada LLM, adicione ao ~/.adforge/.env UMA das:
  ANTHROPIC_API_KEY=...   (usa claude-sonnet-4-6)
  DEEPSEEK_API_KEY=...    (usa deepseek-chat)
"""
import json
from common import f

# custo aproximado por 1k tokens (BRL) só para o tracker de budget
PRICE_BRL = {"anthropic": 0.02, "deepseek": 0.001}


def _phase_roas_min(dias):
    """Retorna o ROAS mínimo aceitável conforme benchmarks_spid.md."""
    if dias is None:
        return 5.0
    if dias > 14:
        return 10.0  # Aquecimento
    if dias > 7:
        return 8.0   # Aceleração
    return 5.0       # Sprint final


def _rule_based(meta, analysis, dias=None):
    roas_min = _phase_roas_min(dias)
    recs = []  # (prioridade, texto, porque, impacto)
    for a in meta.get("adsets", []):
        if f(a.get("freq_7d")) > 8:
            recs.append(("alta",
                "Renovar criativos do conjunto '%s'" % a.get("name"),
                "Frequência 7d %.1f indica saturação da audiência" % f(a.get("freq_7d")),
                "Reduz CPM e recupera CTR"))
    for a in meta.get("adsets", []):
        if f(a.get("spend_24h")) > 0 and 0 < f(a.get("roas_48h")) < roas_min:
            recs.append(("alta",
                "Revisar/realocar verba do conjunto '%s'" % a.get("name"),
                "ROAS 48h %.1fx abaixo do piso de %.0fx (fase atual)" % (f(a.get("roas_48h")), roas_min),
                "Protege o ROAS geral realocando para conjuntos eficientes"))
    if analysis.get("n_zero_delivery", 0) > 0:
        recs.append(("media",
            "Substituir %d anúncio(s) ativo(s) sem entrega" % analysis["n_zero_delivery"],
            "Anúncios ativos sem impressão consomem espaço de aprendizagem",
            "Libera o conjunto para escalar criativos que entregam"))
    for c in analysis.get("top3", [])[:1]:
        recs.append(("media",
            "Escalar +20%% o criativo '%s'" % c.get("name"),
            "Está no top de ROAS (%.1fx) nas últimas 24h" % f(c.get("roas_24h")),
            "Aproveita o melhor desempenho antes de saturar"))
    var = analysis.get("variacoes", {})
    if var.get("purchases") is not None and var["purchases"] < -20:
        recs.append(("alta",
            "Investigar queda de compras (%.0f%% vs ontem)" % var["purchases"],
            "Queda relevante dia a dia pode indicar tracking ou fadiga",
            "Estanca perda de faturamento"))
    if not recs:
        recs.append(("baixa",
            "Manter alocação atual e monitorar",
            "Sem alertas críticos detectados nas últimas 24/48h",
            "Estabilidade; reavaliar amanhã"))
    # dedup + corta em 5, ordenando por prioridade
    ordem = {"alta": 0, "media": 1, "baixa": 2}
    vistos, uniq = set(), []
    for r in sorted(recs, key=lambda x: ordem[x[0]]):
        if r[1] in vistos:
            continue
        vistos.add(r[1])
        uniq.append(r)
    return uniq[:5]


def _llm_provider(env):
    if env.get("ANTHROPIC_API_KEY", "").strip():
        return "anthropic", env["ANTHROPIC_API_KEY"].strip()
    if env.get("DEEPSEEK_API_KEY", "").strip():
        return "deepseek", env["DEEPSEEK_API_KEY"].strip()
    return None, None


def _build_context_block(context):
    """Formata os reference files como bloco de contexto para o LLM."""
    parts = []
    for fname, content in context.items():
        if content.strip():
            parts.append("=== %s ===\n%s" % (fname, content.strip()))
    if not parts:
        return ""
    return "\n\n".join(parts)


def _llm_refine(provider, key, meta, analysis, base, g, context=None, dias=None):
    """Chama o LLM para reescrever as recomendações de forma consultiva."""
    payload = {
        "totais": meta.get("totals"),
        "variacoes": analysis.get("variacoes"),
        "alertas": analysis.get("alertas"),
        "dias_ate_evento": dias,
        "recomendacoes_base": [
            {"prioridade": p, "acao": t, "porque": pq, "impacto": im} for (p, t, pq, im) in base
        ],
    }
    ctx_block = _build_context_block(context or {})
    ctx_section = ("\n\n--- CONTEXTO DE CAMPANHA (use como referência) ---\n" + ctx_block) if ctx_block else ""
    instr = (
        "Você é analista de tráfego pago do AdForge. Reescreva as recomendações para o gestor "
        "da 3ª Etapa SPID CUP 2026 de forma direta e consultiva (linguagem de paddock, sem jargão "
        "corporativo). Use os benchmarks e a estrutura de campanha fornecidos como referência para "
        "calibrar thresholds e prioridades. Máximo 5 recomendações. "
        "Responda APENAS JSON: "
        '{"recomendacoes":[{"prioridade":"alta|media|baixa","acao":"","porque":"","impacto":""}]}'
        + ctx_section + "\n\n--- DADOS DO DIA ---\n"
        + json.dumps(payload, ensure_ascii=False)
    )

    if provider == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        import urllib.request
        body = json.dumps({
            "model": "claude-sonnet-4-6", "max_tokens": 2000,
            "messages": [{"role": "user", "content": instr}],
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json",
        })
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
        txt = "".join(b.get("text", "") for b in data.get("content", []))
        usage = data.get("usage", {})
        toks = (usage.get("input_tokens", 0) + usage.get("output_tokens", 0)) / 1000.0
        g.add_llm_cost(toks * PRICE_BRL["anthropic"])
    else:  # deepseek (OpenAI-compatible)
        import urllib.request
        url = "https://api.deepseek.com/chat/completions"
        body = json.dumps({
            "model": "deepseek-chat", "max_tokens": 1200,
            "messages": [{"role": "user", "content": instr}],
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": "Bearer %s" % key, "content-type": "application/json",
        })
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
        txt = data["choices"][0]["message"]["content"]
        toks = f(data.get("usage", {}).get("total_tokens")) / 1000.0
        g.add_llm_cost(toks * PRICE_BRL["deepseek"])

    s = txt.find("{")
    e = txt.rfind("}")
    parsed = json.loads(txt[s:e + 1])
    out = []
    for r in parsed.get("recomendacoes", [])[:5]:
        out.append((r.get("prioridade", "media"), r.get("acao", ""),
                    r.get("porque", ""), r.get("impacto", "")))
    return out


def recommend(env, meta, analysis, g, context=None, dias=None):
    base = _rule_based(meta, analysis, dias=dias)
    provider, key = _llm_provider(env)
    if not key:
        return base, "rule-based (sem API key de LLM)"
    if not g.budget_ok():
        return base, "rule-based (budget LLM esgotado)"
    try:
        refined = _llm_refine(provider, key, meta, analysis, base, g, context=context, dias=dias)
        if refined:
            return refined, "híbrido (LLM: %s)" % provider
        return base, "rule-based (LLM retornou vazio)"
    except Exception as e:
        return base, "rule-based (LLM falhou: %s)" % str(e)[:80]
