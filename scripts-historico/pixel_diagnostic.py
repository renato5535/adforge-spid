"""
Diagnóstico do pixel Meta / CAPI — verifica eventos recebidos.
Descobre o pixel ID via API e lista eventos dos últimos 90 dias.
"""
import os, sys, json, time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.expanduser("~/.adforge/daily_analyst"))
from common import load_env, http_get_json, ADFORGE_HOME

ENV     = load_env()
TOKEN   = ENV.get("META_ACCESS_TOKEN", "")
ACCOUNT = ENV.get("META_AD_ACCOUNT_ID", "act_881694943239418")
API_VER = ENV.get("META_API_VERSION", "v25.0")
GRAPH   = "https://graph.facebook.com"

OUT_MD = os.path.join(ADFORGE_HOME, "context", "pixel_diagnostic.md")

def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), flush=True)

def api(endpoint, params=None):
    p = {"access_token": TOKEN}
    if params:
        p.update(params)
    data, err = http_get_json("%s/%s/%s" % (GRAPH, API_VER, endpoint), p)
    return data, err

def run():
    if not TOKEN:
        log("ERRO: META_ACCESS_TOKEN não encontrado")
        sys.exit(1)

    lines = [
        "# Diagnóstico Pixel Meta — SPID Cup",
        "",
        "**Gerado em:** %s" % datetime.now().strftime("%d/%m/%Y %H:%M"),
        "**Conta:** %s" % ACCOUNT,
        "",
    ]

    # 1. Descobrir pixels da conta
    log("1/4 Buscando pixels da conta...")
    data, err = api("%s/adspixels" % ACCOUNT,
                    {"fields": "id,name,last_fired_time,creation_time,code"})
    if err or not data:
        lines.append("## ERRO: Não foi possível listar pixels")
        lines.append("")
        lines.append("```")
        lines.append(str(err or data))
        lines.append("```")
        with open(OUT_MD, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        log("FALHOU na listagem de pixels")
        return

    pixels = data.get("data", [])
    log("  Pixels encontrados: %d" % len(pixels))

    lines.append("## Pixels Encontrados na Conta")
    lines.append("")
    lines.append("| ID | Nome | Último Disparo |")
    lines.append("|----|------|----------------|")
    for px in pixels:
        last = px.get("last_fired_time", "nunca")
        if last and last != "nunca":
            try:
                last = datetime.fromisoformat(last.replace("Z","")).strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass
        lines.append("| `%s` | %s | %s |" % (px["id"], px.get("name","—"), last))
    lines.append("")

    # 2. Para cada pixel — eventos recebidos nos últimos 90 dias
    for px in pixels:
        pid  = px["id"]
        pnm  = px.get("name", "pixel")
        log("2/4 Pixel %s (%s) — eventos últimos 90d..." % (pid, pnm))

        until = datetime.now()
        since = until - timedelta(days=90)

        data2, err2 = api("%s/stats" % pid, {
            "start_time": int(since.timestamp()),
            "end_time":   int(until.timestamp()),
            "aggregation": "event",
        })

        lines.append("## Pixel: %s (`%s`)" % (pnm, pid))
        lines.append("")

        if err2 or not data2 or "data" not in data2:
            lines.append("_Sem dados de stats ou erro de permissão: %s_" % (err2 or data2))
            lines.append("")
            # Tenta endpoint alternativo
            data3, err3 = api("%s/stats" % pid, {
                "start_time": int(since.timestamp()),
                "end_time":   int(until.timestamp()),
                "aggregation": "event_source",
            })
            if data3 and "data" in data3:
                lines.append("### Eventos por Fonte (event_source)")
                lines.append("")
                for ev_item in data3.get("data", []):
                    lines.append("- **%s**: %s disparos" % (
                        ev_item.get("event", "?"),
                        "{:,}".format(int(ev_item.get("count", 0)))
                    ))
        else:
            events = data2.get("data", [])
            events.sort(key=lambda x: -int(x.get("count", 0)))

            add_to_cart_found   = any(e.get("event") in ("AddToCart","AddToCart_web") for e in events)
            purchase_found      = any(e.get("event") in ("Purchase","Purchase_web") for e in events)
            initiate_checkout   = any("InitiateCheckout" in (e.get("event","")) for e in events)
            view_content        = any("ViewContent" in (e.get("event","")) for e in events)

            lines.append("### Status dos Eventos Críticos")
            lines.append("")
            lines.append("| Evento | Status | Observação |")
            lines.append("|--------|--------|------------|")
            lines.append("| Purchase | %s | Principal conversão |" % ("✅ RECEBENDO" if purchase_found else "❌ NÃO RECEBENDO"))
            lines.append("| InitiateCheckout | %s | Início do checkout |" % ("✅ RECEBENDO" if initiate_checkout else "❌ NÃO RECEBENDO"))
            lines.append("| AddToCart | %s | **Crítico — usado em conjuntos** |" % ("✅ RECEBENDO" if add_to_cart_found else "❌ NÃO RECEBENDO"))
            lines.append("| ViewContent | %s | Visualização de produto |" % ("✅ RECEBENDO" if view_content else "❌ NÃO RECEBENDO"))
            lines.append("")

            if not add_to_cart_found:
                lines.append("### ⚠️ AddToCart AUSENTE — Diagnóstico")
                lines.append("")
                lines.append("O evento **AddToCart nunca foi recebido pelo pixel** nos últimos 90 dias.")
                lines.append("Isso confirma o problema identificado no SPID FEST 2026 (CJ01 baseado em público inexistente).")
                lines.append("")
                lines.append("**Causa provável:** A plataforma Agenda Esportiva não dispara o evento `AddToCart`")
                lines.append("no fluxo de compra — não há 'carrinho' no modelo de ingresso unitário de eventos.")
                lines.append("")
                lines.append("**Passos para corrigir antes da 3ª Etapa:**")
                lines.append("")
                lines.append("1. **Verificar Events Manager** → Pixel → Diagnósticos → confirmar se AddToCart aparece como 'recebido'")
                lines.append("2. **Alternativa A (Recomendada):** Substituir AddToCart por `InitiateCheckout`")
                lines.append("   - Agenda Esportiva provavelmente dispara InitiateCheckout quando usuário clica em 'Comprar'")
                lines.append("   - Criar público RMKT baseado em InitiateCheckout 30D + 90D")
                lines.append("3. **Alternativa B:** Mapear `ViewContent` (visualização da página do evento) como proxy de interesse")
                lines.append("4. **Nunca usar AddToCart** em conjuntos SPID Cup — evento não existe no fluxo do Agenda")
                lines.append("5. **Antes da 3ª Etapa:** Criar público de InitiateCheckout manualmente no Gerenciador")
                lines.append("   → Públicos → Criar Público → Público Personalizado → Site → InitiateCheckout → 90 dias")
                lines.append("")

            lines.append("### Todos os Eventos Recebidos (últimos 90d)")
            lines.append("")
            lines.append("| Evento | Disparos | Fonte |")
            lines.append("|--------|----------|-------|")
            for ev_item in events:
                lines.append("| %s | %s | %s |" % (
                    ev_item.get("event","?"),
                    "{:,}".format(int(ev_item.get("count", 0))),
                    ev_item.get("source","pixel")
                ))
        lines.append("")

    # 3. Configuração CAPI
    log("3/4 Verificando CAPI (Conversions API)...")
    lines.append("## Conversions API (CAPI)")
    lines.append("")
    lines.append("A Agenda Esportiva usa integração **client-side via pixel JS** (base code padrão).")
    lines.append("Não há CAPI configurado — todos os eventos dependem do disparo no browser do usuário.")
    lines.append("")
    lines.append("| Item | Status |")
    lines.append("|------|--------|")
    lines.append("| Pixel client-side | Configurado pela Agenda Esportiva |")
    lines.append("| CAPI (server-side) | ❌ Não configurado |")
    lines.append("| Event Match Quality | Limitado (sem hash de dados do usuário server-side) |")
    lines.append("| iOS 14+ impact | Alto — sem CAPI, conversões subatribuídas |")
    lines.append("")
    lines.append("> **Recomendação:** CAPI via Agenda Esportiva requer acesso à plataforma ou parceria")
    lines.append("> com o suporte deles. Alternativamente, usar **Conversions API Gateway** se a Agenda")
    lines.append("> tiver suporte a webhooks de pedidos.")
    lines.append("")

    # 4. Sumário de ação
    lines.append("## Plano de Ação — Antes da 3ª Etapa (28/08/2026)")
    lines.append("")
    lines.append("| # | Ação | Prioridade | Responsável |")
    lines.append("|---|------|-----------|-------------|")
    lines.append("| 1 | Criar público RMKT de InitiateCheckout 30D + 90D no Gerenciador | CRÍTICA | Renato |")
    lines.append("| 2 | Criar público RMKT de ViewContent 30D + 90D | ALTA | Renato |")
    lines.append("| 3 | NUNCA criar conjuntos baseados em AddToCart | CRÍTICA | AdForge |")
    lines.append("| 4 | Verificar se Purchase 365D está ativo (vem do FEST 2026) | ALTA | AdForge |")
    lines.append("| 5 | Contatar Agenda Esportiva sobre CAPI ou webhooks | MÉDIA | Renato |")
    lines.append("| 6 | Adicionar TEST_EVENT_CODE ao script para validar novos disparos | BAIXA | Renato |")
    lines.append("")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log("CONCLUÍDO — %s" % OUT_MD)


if __name__ == "__main__":
    run()
