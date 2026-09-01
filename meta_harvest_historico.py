"""
Meta Marketing API — Harvest histórico por janela de evento.

Para cada etapa do Agenda (SPID Cup + SPID Fest Visitantes), define uma
janela de campanha (~45 dias antes até a data do evento) e busca os
insights de Meta Ads (gasto, compras, receita atribuída, ROAS).

Cruza tudo com a receita real do Agenda e salva em:
  ~/.adforge/reports/meta-historico.json
  ~/.adforge/reports/crossref-spid.json   ← relatório cruzado
"""
import os, sys, json, re, time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.expanduser("~/.adforge/daily_analyst"))
from common import load_env, http_get_json, ADFORGE_HOME, f as to_float

ENV          = load_env()
TOKEN        = ENV.get("META_ACCESS_TOKEN", "")
ACCOUNT      = ENV.get("META_AD_ACCOUNT_ID", "act_881694943239418")
API_VER      = ENV.get("META_API_VERSION", "v25.0")
GRAPH        = "https://graph.facebook.com"

OUT_META     = os.path.join(ADFORGE_HOME, "reports", "meta-historico.json")
OUT_CROSS    = os.path.join(ADFORGE_HOME, "reports", "crossref-spid.json")
AGENDA_FILE  = os.path.join(ADFORGE_HOME, "reports", "agenda-historico.json")

PURCHASE_TYPES = ("omni_purchase", "purchase", "offsite_conversion.fb_pixel_purchase")

# Palavras-chave para excluir do Agenda (pilotos, NO PREP, etc.)
EXCLUIR = ("pilotos", "no prep", "inscrição pilotos", "greatest show",
           "inscrição de pilotos", "batalha super carros")


def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), flush=True)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_visitante(etapa):
    nm = (etapa.get("nm_etapa") or etapa.get("nm_evento_pai") or "").lower()
    return not any(k in nm for k in EXCLUIR)


def acted(items, key="actions"):
    if not items:
        return 0.0
    for t in PURCHASE_TYPES:
        for a in items:
            if isinstance(a, dict) and a.get("action_type") == t:
                return to_float(a.get("value", 0))
    return 0.0


def get_meta_insights(since, until, level="account"):
    """
    Busca insights do Meta para um período específico.
    level: "account" | "campaign" | "adset"
    """
    url = "%s/%s/%s/insights" % (GRAPH, API_VER, ACCOUNT)
    params = {
        "level":       level,
        "fields":      ("campaign_name,adset_name,spend,impressions,clicks,"
                        "actions,action_values,frequency,purchase_roas"),
        "time_range":  json.dumps({"since": since, "until": until}),
        "limit":       "500",
        "access_token": TOKEN,
    }
    rows = []
    api_calls = 0
    while url:
        data, err = http_get_json(url, params)
        api_calls += 1
        params = None   # paginação usa URL completa
        if err or (data and "error" in data):
            msg = (data or {}).get("error", {}).get("message", err) if data else err
            log("  API ERRO [%s→%s]: %s" % (since, until, msg))
            break
        rows.extend(data.get("data", []))
        url = (data.get("paging", {}) or {}).get("next")
        if api_calls > 10:   # safety — não excede 10 chamadas por janela
            break
        time.sleep(0.3)
    return rows, api_calls


def aggregate_rows(rows):
    """Agrega múltiplas linhas (campanhas) em totais do período."""
    totals = {"spend": 0, "purchases": 0, "revenue": 0, "impressions": 0, "clicks": 0}
    campaigns = {}
    for r in rows:
        sp  = to_float(r.get("spend", 0))
        pur = acted(r.get("actions"))
        rev = acted(r.get("action_values"), "action_values")
        imp = to_float(r.get("impressions", 0))
        clk = to_float(r.get("clicks", 0))
        totals["spend"]       += sp
        totals["purchases"]   += pur
        totals["revenue"]     += rev
        totals["impressions"] += imp
        totals["clicks"]      += clk
        # Agrupa por campanha
        cn = r.get("campaign_name") or "unknown"
        if cn not in campaigns:
            campaigns[cn] = {"spend": 0, "purchases": 0, "revenue": 0}
        campaigns[cn]["spend"]     += sp
        campaigns[cn]["purchases"] += pur
        campaigns[cn]["revenue"]   += rev

    totals["roas"] = round(totals["revenue"] / totals["spend"], 2) if totals["spend"] else 0
    totals["cpa"]  = round(totals["spend"] / totals["purchases"], 2) if totals["purchases"] else 0
    totals["campaigns"] = campaigns
    return totals


def event_window(dt_etapa_iso, pre_days=45, post_days=1):
    """
    Janela de campanha: [dt_etapa - pre_days, dt_etapa + post_days].
    Para eventos antigos, usa janela menor se o período é desconhecido.
    """
    try:
        dt = datetime.strptime(dt_etapa_iso[:10], "%Y-%m-%d")
    except Exception:
        return None, None
    since = (dt - timedelta(days=pre_days)).strftime("%Y-%m-%d")
    until = (dt + timedelta(days=post_days)).strftime("%Y-%m-%d")
    return since, until


def run():
    if not TOKEN:
        log("ERRO: META_ACCESS_TOKEN não encontrado no .env")
        sys.exit(1)

    # Carrega etapas do Agenda (somente visitantes com data)
    agenda = load_json(AGENDA_FILE)
    etapas = [
        e for e in agenda.get("etapas", [])
        if is_visitante(e) and e.get("dt_etapa") and e.get("vl_inscricoes", 0)
    ]
    etapas.sort(key=lambda x: x.get("dt_etapa") or "")
    log("Etapas a cruzar: %d" % len(etapas))

    meta_results = []
    crossref     = []
    total_calls  = 0

    for i, et in enumerate(etapas):
        nm    = (et.get("nm_etapa") or et.get("nm_evento_pai") or "?")[:50]
        dt    = et.get("dt_etapa", "")[:10]
        vl_ag = et.get("vl_inscricoes") or et.get("vl_total") or 0

        since, until = event_window(dt)
        if not since:
            log("[%d/%d] SKIP %s — sem data" % (i+1, len(etapas), nm))
            continue

        log("[%d/%d] %s | %s → %s" % (i+1, len(etapas), nm[:40], since, until))

        rows, calls = get_meta_insights(since, until, level="campaign")
        total_calls += calls

        totals = aggregate_rows(rows)
        roas_real = round(vl_ag / totals["spend"], 2) if totals["spend"] else None

        meta_row = {
            "dt_evento":   dt,
            "nm_etapa":    nm,
            "since":       since,
            "until":       until,
            "meta":        totals,
            "agenda_receita": vl_ag,
            "roas_real_agenda": roas_real,
        }
        meta_results.append(meta_row)

        crossref.append({
            "evento":          nm,
            "data":            dt,
            "janela":          "%s → %s" % (since, until),
            "meta_spend":      round(totals["spend"], 2),
            "meta_purchases":  round(totals["purchases"], 0),
            "meta_revenue_atrib": round(totals["revenue"], 2),
            "meta_roas_atrib": totals["roas"],
            "agenda_receita":  round(vl_ag, 2),
            "roas_real":       roas_real,
            "meta_campanhas":  list(totals["campaigns"].keys()),
        })

        log("  Spend: R$%.0f | Compras Meta: %.0f | Receita Meta: R$%.0f | ROAS atrib: %.1fx | Receita Agenda: R$%.0f | ROAS real: %sx" % (
            totals["spend"], totals["purchases"], totals["revenue"],
            totals["roas"], vl_ag, roas_real or "?",
        ))

        time.sleep(0.5)   # gentil com a API

    # Salva arquivos
    save_json(OUT_META,  {"gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          "total_api_calls": total_calls, "eventos": meta_results})
    save_json(OUT_CROSS, {"gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          "total_api_calls": total_calls, "crossref": crossref})

    # Relatório final
    print("\n" + "=" * 90)
    print("CROSSREF META × AGENDA — SPID Cup + SPID Fest (Visitantes)")
    print("=" * 90)
    print("%-10s %-42s %10s %8s %10s %10s %8s" % (
        "Data", "Evento", "Spend Meta", "Compras", "Rec Meta", "Rec Agenda", "ROAS Real"))
    print("-" * 90)

    tot_spend = tot_pur = tot_rev_m = tot_rev_a = 0
    for r in crossref:
        sp  = r["meta_spend"]
        pur = r["meta_purchases"]
        rm  = r["meta_revenue_atrib"]
        ra  = r["agenda_receita"]
        rr  = r["roas_real"]
        tot_spend  += sp
        tot_pur    += pur
        tot_rev_m  += rm
        tot_rev_a  += ra
        print("%-10s %-42s %10.0f %8.0f %10.0f %10.0f %8s" % (
            r["data"][:10], r["evento"][:42], sp, pur, rm, ra,
            ("%.1fx" % rr) if rr else "  ?",
        ))

    print("-" * 90)
    tot_roas_real = round(tot_rev_a / tot_spend, 1) if tot_spend else 0
    print("%-10s %-42s %10.0f %8.0f %10.0f %10.0f %8s" % (
        "TOTAL", "", tot_spend, tot_pur, tot_rev_m, tot_rev_a,
        "%.1fx" % tot_roas_real,
    ))
    print("\nAPI calls usadas: %d | Arquivos: %s" % (total_calls, OUT_CROSS))

    return crossref


if __name__ == "__main__":
    run()
