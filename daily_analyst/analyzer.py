"""Passo C — Análise determinística sobre os dados coletados.

Calcula variações, rankings e os alertas definidos no spec. Tudo por regras —
nada de LLM aqui (a camada consultiva fica no recommender, opcional).
"""
from common import f, pct

META_TICKET = 2000          # teto de ingressos da 3ª Etapa SPID Cup
FREQ_FADIGA = 8.0           # alerta de fadiga
ROAS_QUEDA = 5.0            # alerta de queda (48h)

META_FATURAMENTO = 140_000.0
META_FAT_SUCESSO = 130_000.0
META_FAT_ACEITAVEL = 100_000.0


def _pacing(meta, agenda, dias_ate_evento):
    """Calcula projeção de faturamento e sinal de escalação de budget."""
    t = meta.get("totals", {})
    ab = meta.get("account_balance", {})
    sp7 = f(t.get("spend_7d"))
    val7 = f(t.get("value_7d"))
    roas7 = f(t.get("roas_7d"))
    remaining = ab.get("balance")

    daily_spend = sp7 / 7.0 if sp7 else None
    daily_revenue = val7 / 7.0 if val7 else None
    fuel_days = (remaining / daily_spend) if (remaining and daily_spend) else None

    fat_atual = None
    if agenda.get("status") in ("ok", "parcial"):
        fat_atual = agenda.get("vl_inscricoes")

    # Projeção: faturamento já feito + o que o saldo restante deve gerar (ROAS Meta-atribuído 7d)
    projected = None
    if fat_atual is not None and remaining is not None and roas7:
        projected = fat_atual + remaining * roas7

    gap = (META_FATURAMENTO - projected) if projected is not None else None

    if projected is None:
        tier = None
    elif projected >= 150_000:
        tier = "superacao"
    elif projected >= META_FAT_SUCESSO:
        tier = "sucesso"
    elif projected >= META_FAT_ACEITAVEL:
        tier = "aceitavel"
    else:
        tier = "fracasso"

    escalation_signal = tier in ("sucesso", "superacao") if tier else False

    rev_needed_daily = None
    if fat_atual is not None and dias_ate_evento > 0:
        rev_gap = META_FATURAMENTO - fat_atual
        if rev_gap > 0:
            rev_needed_daily = rev_gap / dias_ate_evento

    return {
        "remaining_balance": remaining,
        "daily_spend": daily_spend,
        "daily_revenue": daily_revenue,
        "fuel_days": fuel_days,
        "fat_atual": fat_atual,
        "projected": projected,
        "gap": gap,
        "tier": tier,
        "escalation_signal": escalation_signal,
        "rev_needed_daily": rev_needed_daily,
        "roas_7d": roas7,
    }


def analyze(meta, agenda, dias_ate_evento):
    t = meta.get("totals", {})
    campaigns = meta.get("campaigns", [])
    adsets = meta.get("adsets", [])
    ads = meta.get("ads", [])

    # variações dia anterior -> ontem
    var = {
        "spend": pct(t.get("spend_24h"), t.get("spend_prev")),
        "purchases": pct(t.get("purchases_24h"), t.get("purchases_prev")),
        "roas": pct(t.get("roas_24h"),
                    (f(t.get("value_prev")) / f(t.get("spend_prev"))) if f(t.get("spend_prev")) else 0),
    }

    # rankings de criativos por ROAS (só os que entregaram)
    entregues = [a for a in ads if a.get("delivered_24h") and f(a.get("spend_24h")) > 0]
    por_roas = sorted(entregues, key=lambda a: f(a.get("roas_24h")), reverse=True)
    top3 = por_roas[:3]
    bottom3 = list(reversed(por_roas[-3:])) if len(por_roas) >= 3 else por_roas[::-1]

    # conjuntos top/bottom por ROAS 24h (para a tabela do relatório)
    adsets_roas = sorted(adsets, key=lambda a: f(a.get("roas_24h")), reverse=True)

    # alertas
    alertas = []
    for a in adsets:
        if f(a.get("freq_7d")) > FREQ_FADIGA:
            alertas.append("🔥 Fadiga: conjunto '%s' com frequência 7d %.1f (> %.0f)"
                           % (a.get("name"), f(a.get("freq_7d")), FREQ_FADIGA))
    for a in adsets:
        if f(a.get("spend_24h")) > 0 and 0 < f(a.get("roas_48h")) < ROAS_QUEDA:
            alertas.append("📉 Queda: conjunto '%s' com ROAS 48h %.1fx (< %.0f)"
                           % (a.get("name"), f(a.get("roas_48h")), ROAS_QUEDA))
    zero = meta.get("zero_delivery", [])
    for z in zero[:10]:
        alertas.append("🚫 Sem entrega: anúncio ativo '%s' com 0 entrega nas últimas 24h" % z.get("name"))

    # ingressos vendidos (preferir Agenda; senão indisponível)
    vendidos = agenda.get("total_vendido") if agenda.get("status") in ("ok", "parcial") else None

    return {
        "variacoes": var,
        "top3": top3,
        "bottom3": bottom3,
        "adsets_ranked": adsets_roas,
        "alertas": alertas,
        "vendidos": vendidos,
        "meta_ticket": META_TICKET,
        "dias_ate_evento": dias_ate_evento,
        "n_entregando": len(entregues),
        "n_zero_delivery": len(zero),
        "pacing": _pacing(meta, agenda, dias_ate_evento),
    }
