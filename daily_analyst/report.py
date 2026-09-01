"""Passo E — Monta o relatório markdown no template obrigatório da ETAPA 3."""
from common import brl, f, pct_str, now_sp

PRIOR = [("alta", "🔴 Alta prioridade"), ("media", "🟡 Média prioridade"), ("baixa", "🟢 Baixa prioridade")]


def _row(c):
    return "| %s | %s | %s | %s | %s | %.1fx | %.1f |" % (
        c.get("name", "")[:42], c.get("status", "ACTIVE"),
        brl(c.get("spend_24h")), int(f(c.get("purchases_24h"))),
        brl(c.get("cpa_24h")), f(c.get("roas_24h")), f(c.get("freq_24h")))


def build(meta, agenda, analysis, recs, recs_source, gmetrics):
    t = meta.get("totals", {})
    a = analysis
    L = []
    ts = now_sp().strftime("%Y-%m-%d %H:%M")
    L.append("# Relatório Diário AdForge — 3ª Etapa SPID Cup 2026")
    L.append("**Data:** %s" % ts)
    L.append("**Execução:** %ss | %s/%s chamadas API | LLM %s/R$%s (%s)" % (
        gmetrics["elapsed_seconds"], gmetrics["api_calls"], gmetrics["max_api_calls"],
        brl(gmetrics["llm_brl"]).replace("R$ ", "R$"), gmetrics["max_llm_brl"], recs_source))
    if gmetrics.get("truncated"):
        L.append("> ⚠️ **Execução truncada:** %s — relatório parcial." % gmetrics.get("truncate_reason"))
    L.append("")

    # Visão geral
    L.append("## 📊 Visão Geral")
    if a.get("vendidos") is not None:
        v = a["vendidos"]
        res = agenda.get("reservados")
        res_str = (" + %d reservados" % res) if res else ""
        L.append("- **Ingressos vendidos:** %s%s / %s (%.1f%% do teto)" % (v, res_str, a["meta_ticket"], v / a["meta_ticket"] * 100))
    elif agenda.get("status") == "evento_nao_cadastrado":
        L.append("- **Ingressos vendidos:** _Evento ainda não cadastrado na Agenda Esportiva_")
    else:
        L.append("- **Ingressos vendidos:** _Agenda indisponível_ (%s)" % agenda.get("motivo", "—"))
    if agenda.get("status") in ("ok", "parcial"):
        vl_i = agenda.get("vl_inscricoes")
        vl_r = agenda.get("vl_total")
        if vl_i is not None:
            L.append("- **Valor de Inscrições (referência):** %s" % brl(vl_i))
            if vl_r is not None:
                L.append("- **A Receber (líquido Agenda):** %s" % brl(vl_r))
        else:
            L.append("- **Faturamento (Agenda):** %s" % (agenda.get("faturamento") or "_não capturado_"))
    ab = meta.get("account_balance", {})
    bal = ab.get("balance")
    if bal is not None:
        alerta_saldo = " ⚠️ RECARREGAR" if bal < 1200 else (" ⚡ MONITORAR" if bal < 3000 else "")
        L.append("- **Saldo Meta (pré-pago):** %s%s" % (brl(bal), alerta_saldo))
    elif ab.get("display_string"):
        L.append("- **Saldo Meta (pré-pago):** %s" % ab["display_string"])
    if ab.get("amount_spent") is not None:
        L.append("- **Gasto acumulado (conta, histórico):** %s" % brl(ab["amount_spent"]))
    L.append("- **Dias até o evento:** %s" % a.get("dias_ate_evento", "—"))
    L.append("")

    # Pacing
    pac = a.get("pacing", {})
    fat = pac.get("fat_atual")
    proj = pac.get("projected")
    if fat is not None or pac.get("remaining_balance") is not None:
        L.append("## 🏃 Pacing — Projeção de Faturamento")
        META_FAT = 140_000.0
        if fat is not None:
            L.append("- **Faturamento atual (Agenda):** %s (%.1f%% da meta)" % (
                brl(fat), fat / META_FAT * 100))
        if proj is not None:
            tier_labels = {
                "superacao": "🚀 Superação (>R$150k)",
                "sucesso":   "✅ Sucesso (R$130–150k)",
                "aceitavel": "⚠️ Aceitável (R$100–130k)",
                "fracasso":  "❌ Fracasso (<R$100k)",
            }
            roas7 = pac.get("roas_7d", 0)
            L.append("- **Projeção final** (ROAS 7d Meta %.1fx × saldo)**:** %s — %s" % (
                roas7, brl(proj), tier_labels.get(pac.get("tier", ""), "—")))
            gap = pac.get("gap")
            if gap is not None and gap > 0:
                L.append("- **Gap para meta:** %s" % brl(gap))
        rb = pac.get("remaining_balance")
        if rb is not None:
            L.append("- **Saldo restante (combustível):** %s" % brl(rb))
        fdays = pac.get("fuel_days")
        dias = a.get("dias_ate_evento") or 0
        if fdays is not None and dias:
            ok = "✅ suficiente" if fdays >= dias else "⚠️ insuficiente"
            L.append("- **Duração do orçamento:** %.1f dias ao ritmo atual — %s" % (fdays, ok))
        ds = pac.get("daily_spend")
        dr = pac.get("daily_revenue")
        if ds is not None:
            L.append("- **Ritmo 7d:** Gasto %s/dia · Receita Meta %s/dia" % (
                brl(ds), brl(dr or 0)))
        rn = pac.get("rev_needed_daily")
        if rn is not None:
            L.append("- **Receita diária necessária:** %s/dia para atingir R$140k" % brl(rn))
        if pac.get("escalation_signal"):
            L.append(
                "\n> 💰 **Pacing positivo** — projeção ≥ R$130k. "
                "Momento favorável para solicitar aumento de orçamento.")
        L.append("")

    # Performance por janela temporal
    L.append("## 📈 Performance Meta — Janelas Temporais")
    L.append("| Janela | Gasto | Compras | ROAS | CPA |")
    L.append("|--------|-------|---------|------|-----|")
    for label, sk, vk, pk in [
        ("24h (ontem)", "spend_24h", "value_24h", "purchases_24h"),
        ("3 dias",      "spend_3d",  "value_3d",  "purchases_3d"),
        ("7 dias",      "spend_7d",  "value_7d",  "purchases_7d"),
    ]:
        sp = f(t.get(sk))
        pu = f(t.get(pk))
        ro = f(t.get(vk)) / sp if sp else 0.0
        cpa = sp / pu if pu else 0.0
        L.append("| %s | %s | %d | %.1fx | %s |" % (label, brl(sp), int(pu), ro, brl(cpa) if pu else "—"))
    L.append("_Variação 24h vs anterior: Gasto %s · Compras %s · ROAS %s_" % (
        pct_str(a["variacoes"]["spend"]), pct_str(a["variacoes"]["purchases"]), pct_str(a["variacoes"]["roas"])))
    L.append("")

    # Por campanha
    L.append("## 🎯 Por Campanha")
    L.append("| Campanha | Status | Gasto 24h | Compras 24h | CPA | ROAS | Freq |")
    L.append("|---|---|---|---|---|---|---|")
    for c in sorted(meta.get("campaigns", []), key=lambda x: f(x.get("spend_24h")), reverse=True):
        L.append(_row(c))
    L.append("")

    # Por conjunto
    L.append("## 📦 Por Conjunto (top 5 + bottom 3)")
    L.append("| Conjunto | Gasto 24h | Compras | CPA | ROAS | Freq 7d | ROAS 48h |")
    L.append("|---|---|---|---|---|---|---|")
    ranked = a.get("adsets_ranked", [])
    sel = ranked[:5] + ([("...",)] if len(ranked) > 8 else []) + ranked[-3:] if len(ranked) > 8 else ranked
    for s in sel:
        if isinstance(s, tuple):
            L.append("| … | | | | | | |")
            continue
        L.append("| %s | %s | %d | %s | %.1fx | %.1f | %.1fx |" % (
            s.get("name", "")[:40], brl(s.get("spend_24h")), int(f(s.get("purchases_24h"))),
            brl(s.get("cpa_24h")), f(s.get("roas_24h")), f(s.get("freq_7d")), f(s.get("roas_48h"))))
    L.append("")

    # Criativos
    L.append("## 🎨 Top 3 Criativos")
    if a["top3"]:
        for c in a["top3"]:
            L.append("- **%s** — ROAS %.1fx · %s gasto · %d compras" % (
                c.get("name", "")[:50], f(c.get("roas_24h")), brl(c.get("spend_24h")), int(f(c.get("purchases_24h")))))
    else:
        L.append("- _Sem criativos com entrega nas últimas 24h_")
    L.append("")
    L.append("## ⚠️ Bottom 3 Criativos (candidatos a substituição)")
    if a["bottom3"]:
        for c in a["bottom3"]:
            L.append("- **%s** — ROAS %.1fx · %s gasto · %d compras" % (
                c.get("name", "")[:50], f(c.get("roas_24h")), brl(c.get("spend_24h")), int(f(c.get("purchases_24h")))))
    else:
        L.append("- _Dados insuficientes_")
    L.append("")

    # Alertas
    L.append("## 🚨 Alertas")
    if a["alertas"]:
        for al in a["alertas"]:
            L.append("- %s" % al)
    else:
        L.append("- Nenhum alerta crítico")
    L.append("")

    # Recomendações
    L.append("## 💡 Recomendações Priorizadas")
    for chave, titulo in PRIOR:
        grupo = [r for r in recs if r[0] == chave]
        if not grupo:
            continue
        L.append("### %s" % titulo)
        for i, (_, acao, porque, impacto) in enumerate(grupo, 1):
            L.append("%d. **%s** — %s — _%s_" % (i, acao, porque, impacto))
        L.append("")

    # Anexos
    L.append("## 📎 Anexos")
    L.append("- Screenshot Agenda: %s" % (agenda.get("screenshot") or "—"))
    L.append("- Erros de coleta Meta: %s" % (", ".join(meta.get("errors", [])) or "nenhum"))
    return "\n".join(L)


def summary_for_telegram(meta, agenda, analysis, recs, report_path, gmetrics):
    """Resumo executivo enviado no Telegram (curto)."""
    t = meta.get("totals", {})
    a = analysis
    L = []
    L.append("🏁 AdForge — 3ª Etapa SPID Cup | %s" % now_sp().strftime("%d/%m %H:%M"))
    if a.get("vendidos") is not None:
        v = a["vendidos"]
        extras = []
        if agenda.get("reservados"):
            extras.append("+%d res" % agenda["reservados"])
        vl_i = agenda.get("vl_inscricoes")
        if vl_i is not None:
            extras.append(brl(vl_i))
        elif agenda.get("faturamento"):
            extras.append(agenda["faturamento"])
        suffix = (" (%s)" % " | ".join(extras)) if extras else ""
        L.append("🎟️ Ingressos: %s/%s (%.1f%%)%s" % (v, a["meta_ticket"], v / a["meta_ticket"] * 100, suffix))
    elif agenda.get("status") == "evento_nao_cadastrado":
        L.append("🎟️ Ingressos: evento não cadastrado ainda")
    else:
        L.append("🎟️ Ingressos: Agenda indisponível")
    L.append("💸 Gasto: 24h %s (%s) | 3d %s | 7d %s" % (
        brl(t.get("spend_24h")), pct_str(a["variacoes"]["spend"]),
        brl(t.get("spend_3d")), brl(t.get("spend_7d"))))
    L.append("🛒 Compras: 24h %d (%s) | 3d %d | 7d %d" % (
        int(f(t.get("purchases_24h"))), pct_str(a["variacoes"]["purchases"]),
        int(f(t.get("purchases_3d"))), int(f(t.get("purchases_7d")))))
    L.append("📈 ROAS: 24h %.1fx | 3d %.1fx | 7d %.1fx" % (
        f(t.get("roas_24h")), f(t.get("roas_3d")), f(t.get("roas_7d"))))
    L.append("📅 Faltam %s dias | 🎟️ meta: %s ingressos" % (a.get("dias_ate_evento", "—"), a.get("meta_ticket", "—")))
    pac = a.get("pacing", {})
    if pac.get("projected") is not None:
        tier_emoji = {"superacao": "🚀", "sucesso": "✅", "aceitavel": "⚠️", "fracasso": "❌"}
        em = tier_emoji.get(pac.get("tier", ""), "📊")
        signal = " 💰 SOLICITAR +" if pac.get("escalation_signal") else ""
        L.append("%s Projeção: %s | Saldo: %s%s" % (
            em, brl(pac["projected"]), brl(pac.get("remaining_balance") or 0), signal))
    elif pac.get("remaining_balance") is not None:
        L.append("💰 Saldo combustível: %s" % brl(pac["remaining_balance"]))
    ab = meta.get("account_balance", {})
    bal = ab.get("balance")
    if bal is not None:
        alerta = " ⚠️ RECARREGAR" if bal < 1200 else (" ⚡ MONITORAR" if bal < 3000 else "")
        L.append("💰 Saldo conta: %s%s" % (brl(bal), alerta))
    elif ab.get("display_string"):
        L.append("💰 %s" % ab["display_string"])
    L.append("")
    if a["alertas"]:
        L.append("🚨 Alertas (%d):" % len(a["alertas"]))
        for al in a["alertas"][:5]:
            L.append("• %s" % al)
    else:
        L.append("🚨 Sem alertas críticos")
    L.append("")
    L.append("💡 Top recomendações:")
    for (prio, acao, _, _) in recs[:3]:
        L.append("• [%s] %s" % (prio.upper(), acao))
    if gmetrics.get("truncated"):
        L.append("\n⚠️ Execução truncada: %s" % gmetrics.get("truncate_reason"))
    L.append("\n📄 Relatório completo: %s" % report_path)
    return "\n".join(L)
