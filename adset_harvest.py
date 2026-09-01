"""
Harvest de adsets/públicos por evento — nível adset da Meta API.
Gera ~/.adforge/context/historico_publicos.md organizado por evento.
"""
import os, sys, json, time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.expanduser("~/.adforge/daily_analyst"))
from common import load_env, http_get_json, ADFORGE_HOME, f as to_float

ENV     = load_env()
TOKEN   = ENV.get("META_ACCESS_TOKEN", "")
ACCOUNT = ENV.get("META_AD_ACCOUNT_ID", "act_881694943239418")
API_VER = ENV.get("META_API_VERSION", "v25.0")
GRAPH   = "https://graph.facebook.com"

AGENDA_FILE  = os.path.join(ADFORGE_HOME, "reports", "agenda-historico.json")
OUT_JSON     = os.path.join(ADFORGE_HOME, "context", "historico_publicos.json")
OUT_MD       = os.path.join(ADFORGE_HOME, "context", "historico_publicos.md")

EXCLUIR = ("pilotos", "no prep", "inscrição pilotos", "greatest show",
           "inscrição de pilotos", "batalha super carros")

PURCHASE_TYPES = ("omni_purchase", "purchase", "offsite_conversion.fb_pixel_purchase")

def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), flush=True)

def is_visitante(e):
    nm = (e.get("nm_etapa") or e.get("nm_evento_pai") or "").lower()
    return not any(k in nm for k in EXCLUIR)

def acted(items, key="actions"):
    if not items:
        return 0.0
    for t in PURCHASE_TYPES:
        for a in items:
            if isinstance(a, dict) and a.get("action_type") == t:
                return to_float(a.get("value", 0))
    return 0.0

def event_window(dt_iso, pre=45, post=1):
    try:
        dt = datetime.strptime(dt_iso[:10], "%Y-%m-%d")
    except Exception:
        return None, None
    return (dt - timedelta(days=pre)).strftime("%Y-%m-%d"), \
           (dt + timedelta(days=post)).strftime("%Y-%m-%d")

def get_adset_insights(since, until):
    url    = "%s/%s/%s/insights" % (GRAPH, API_VER, ACCOUNT)
    params = {
        "level":   "adset",
        "fields":  ("campaign_name,adset_name,adset_id,spend,impressions,clicks,"
                    "frequency,actions,action_values,cpm,ctr,cpc"),
        "time_range": json.dumps({"since": since, "until": until}),
        "limit":   "500",
        "access_token": TOKEN,
    }
    rows, calls = [], 0
    while url:
        data, err = http_get_json(url, params)
        calls += 1
        params = None
        if err or (data and "error" in data):
            msg = (data or {}).get("error", {}).get("message", err) if data else err
            log("  API ERR [%s→%s]: %s" % (since, until, msg))
            break
        rows.extend(data.get("data", []))
        url = (data.get("paging", {}) or {}).get("next")
        if calls > 15:
            break
        time.sleep(0.3)
    return rows, calls

def classify_audience(adset_name):
    nm = adset_name.lower()
    if "lkl" in nm or "lookalike" in nm or "semelhante" in nm:
        if "pageview" in nm or "page view" in nm:
            return "LKL Pageview"
        if "purchase" in nm or "compra" in nm:
            return "LKL Purchase"
        if "video" in nm:
            return "LKL Video Views"
        return "LKL (outro)"
    if "engajamento" in nm or "engagement" in nm or "eng " in nm:
        return "Engajamento FB/IG"
    if "pageview" in nm or "page view" in nm or "visitante" in nm:
        return "Visitantes/Pageview"
    if "purchase" in nm or "compra" in nm or "conversa" in nm:
        return "Purchase RMKT"
    if "seguidores" in nm or "follower" in nm:
        return "Seguidores"
    if "video" in nm and ("95" in nm or "75" in nm or "50" in nm):
        return "Video Views RMKT"
    if "interesses" in nm or "interest" in nm or "sport" in nm or "racing" in nm:
        return "Interesses (Frio)"
    if "broad" in nm or "aberto" in nm or "sem segmenta" in nm:
        return "Broad (Frio)"
    return "Outro"

def format_brl(v):
    return "R$%,.0f" % v if v else "—"

def run():
    if not TOKEN:
        log("ERRO: META_ACCESS_TOKEN não encontrado")
        sys.exit(1)

    agenda = json.load(open(AGENDA_FILE, encoding="utf-8"))
    etapas = [
        e for e in agenda.get("etapas", [])
        if is_visitante(e) and e.get("dt_etapa") and e.get("vl_inscricoes", 0)
        and e.get("dt_etapa", "")[:4] >= "2023"  # somente 2023+
    ]
    etapas.sort(key=lambda x: x.get("dt_etapa") or "")
    log("Eventos 2023+: %d" % len(etapas))

    resultado = []

    for i, et in enumerate(etapas):
        nm  = (et.get("nm_etapa") or et.get("nm_evento_pai") or "?")[:60]
        dt  = et.get("dt_etapa", "")[:10]
        vl  = et.get("vl_inscricoes") or 0
        since, until = event_window(dt)
        if not since:
            continue

        log("[%d/%d] %s (%s)" % (i+1, len(etapas), nm, dt))
        rows, calls = get_adset_insights(since, until)

        if not rows:
            log("  Sem dados de adset (período pode ser anterior ao token)")
            resultado.append({"evento": nm, "dt": dt, "agenda_fat": vl,
                               "sem_dados": True, "adsets": []})
            continue

        adsets = []
        for r in rows:
            sp  = to_float(r.get("spend", 0))
            if sp < 0.5:
                continue  # ignora adsets com spend irrelevante
            pur = acted(r.get("actions"))
            rev = acted(r.get("action_values"), "action_values")
            adsets.append({
                "campanha":  r.get("campaign_name", "")[:70],
                "adset":     r.get("adset_name", ""),
                "tipo":      classify_audience(r.get("adset_name", "")),
                "spend":     round(sp, 2),
                "impressoes": int(to_float(r.get("impressions", 0))),
                "cliques":   int(to_float(r.get("clicks", 0))),
                "freq":      round(to_float(r.get("frequency", 0)), 1),
                "cpm":       round(to_float(r.get("cpm", 0)), 2),
                "ctr":       round(to_float(r.get("ctr", 0)), 2),
                "compras":   round(pur, 0),
                "receita":   round(rev, 2),
                "roas_atrib": round(rev/sp, 1) if sp else 0,
            })
        adsets.sort(key=lambda x: x["spend"], reverse=True)

        total_spend = sum(a["spend"] for a in adsets)
        roas_real   = round(vl / total_spend, 1) if total_spend else None

        resultado.append({
            "evento":     nm,
            "dt":         dt,
            "agenda_fat": vl,
            "spend_total": round(total_spend, 2),
            "roas_real":  roas_real,
            "adsets":     adsets,
        })
        log("  %d adsets | Spend R$%.0f | ROAS real %sx" % (
            len(adsets), total_spend, roas_real or "?"))
        time.sleep(0.5)

    # Salva JSON
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    json.dump({"gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
               "eventos": resultado}, open(OUT_JSON, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # Gera Markdown
    lines = [
        "# Histórico de Públicos Meta Ads por Evento — SPID Cup 2023–2026",
        "",
        "**Gerado em:** %s" % datetime.now().strftime("%d/%m/%Y %H:%M"),
        "**Fonte:** Meta Ads API · nível adset · conta %s" % ACCOUNT,
        "**Escopo:** Janelas de 45 dias antes de cada evento + 1 dia após",
        "",
        "---",
        "",
    ]

    for ev in resultado:
        lines.append("## %s — %s" % (ev["dt"][:7], ev["evento"]))
        lines.append("")
        if ev.get("sem_dados"):
            lines.append("_Sem dados de adset disponíveis na janela da API (evento pré-Jun/2023 ou token com cobertura limitada)_")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        lines.append("| KPI | Valor |")
        lines.append("|-----|-------|")
        lines.append("| Faturamento Agenda | %s |" % format_brl(ev["agenda_fat"]))
        lines.append("| Meta Spend Total | %s |" % format_brl(ev["spend_total"]))
        lines.append("| ROAS Real | %sx |" % (ev["roas_real"] or "?"))
        lines.append("")
        lines.append("### Adsets")
        lines.append("")
        lines.append("| Tipo de Público | Adset | Spend | Freq | CPM | Compras Meta | ROAS Atrib |")
        lines.append("|-----------------|-------|-------|------|-----|-------------|------------|")
        for a in ev["adsets"]:
            lines.append("| %s | %s | %s | %.1f | R$%.0f | %.0f | %.1fx |" % (
                a["tipo"], a["adset"][:50],
                format_brl(a["spend"]), a["freq"],
                a["cpm"], a["compras"], a["roas_atrib"]
            ))
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    log("CONCLUÍDO — %s" % OUT_MD)
    return resultado


if __name__ == "__main__":
    run()
