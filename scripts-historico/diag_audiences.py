"""
Diagnóstico: Purchase 730D vs Purchase 180D — por que 730D está vazio?
Salva resultado em ~/.adforge/context/diag_purchase_730d.json
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
OUT     = os.path.join(ADFORGE_HOME, "context", "diag_purchase_730d.json")

def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), flush=True)

def api(endpoint, params=None):
    p = {"access_token": TOKEN}
    if params:
        p.update(params)
    url = endpoint if endpoint.startswith("http") else "%s/%s/%s" % (GRAPH, API_VER, endpoint)
    data, err = http_get_json(url, p)
    return data, err

def paginate(endpoint, params, max_pages=5):
    p = {"access_token": TOKEN}
    if params:
        p.update(params)
    url = endpoint if endpoint.startswith("http") else "%s/%s/%s" % (GRAPH, API_VER, endpoint)
    results = []
    pages = 0
    while url and pages < max_pages:
        data, err = http_get_json(url, p)
        p = None  # paginação usa URL completa
        if err or not data:
            log("  ERRO: %s" % (err or "sem dados"))
            break
        results.extend(data.get("data", []))
        url = (data.get("paging", {}) or {}).get("next")
        pages += 1
        time.sleep(0.3)
    return results

def run():
    if not TOKEN:
        log("ERRO: META_ACCESS_TOKEN ausente")
        sys.exit(1)

    result = {
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "conta": ACCOUNT,
    }

    # ── 1. Listar todas as custom audiences ──────────────────────────────────
    log("1/5 Listando custom audiences da conta...")
    audiences = paginate(
        "%s/customaudiences" % ACCOUNT,
        {"fields": "id,name,approximate_count_lower_bound,approximate_count_upper_bound,"
                   "subtype,time_created,time_updated,description,retention_days,"
                   "rule,lookalike_spec,pixel_id,data_source",
         "limit": "100"},
        max_pages=10
    )
    log("  Encontradas: %d audiências" % len(audiences))

    # ── 2. Separar as de Purchase ─────────────────────────────────────────────
    purchase_audiences = [a for a in audiences if "purchase" in (a.get("name") or "").lower()]
    log("  Audiências com 'purchase' no nome: %d" % len(purchase_audiences))
    for a in purchase_audiences:
        lo = a.get("approximate_count_lower_bound", -1)
        hi = a.get("approximate_count_upper_bound", -1)
        log("    [%s] %s | tamanho: %s–%s | retention: %s dias" % (
            a["id"], a.get("name","?"), lo, hi, a.get("retention_days","?")))

    result["purchase_audiences_raw"] = purchase_audiences
    result["purchase_audiences_count"] = len(purchase_audiences)

    # ── 3. Buscar configuração detalhada de cada Purchase audience ────────────
    log("2/5 Detalhando configuração de cada audiência Purchase...")
    detailed = []
    for a in purchase_audiences:
        aid = a["id"]
        d, err = api("%s" % aid, {
            "fields": "id,name,approximate_count_lower_bound,approximate_count_upper_bound,"
                      "subtype,retention_days,rule,pixel_id,data_source,time_created,"
                      "time_updated,delivery_status,operation_status"
        })
        if err or not d:
            log("  ERRO ao detalhar %s: %s" % (aid, err))
            detailed.append({"id": aid, "erro": str(err)})
        else:
            # Parsear a rule para extrair evento e janela
            rule_raw = d.get("rule", "{}")
            try:
                rule = json.loads(rule_raw) if isinstance(rule_raw, str) else rule_raw
            except Exception:
                rule = {"parse_error": str(rule_raw)[:200]}
            d["rule_parsed"] = rule
            detailed.append(d)
            lo = d.get("approximate_count_lower_bound", -1)
            hi = d.get("approximate_count_upper_bound", -1)
            status = (d.get("delivery_status") or {})
            log("  [%s] %s | tamanho: %s–%s | status: %s | pixel: %s" % (
                aid, d.get("name","?"), lo, hi,
                status.get("code","?") if isinstance(status,dict) else status,
                d.get("pixel_id","?")))
        time.sleep(0.3)

    result["purchase_audiences_detail"] = detailed

    # ── 4. Eventos Purchase no pixel nos últimos 730 dias ────────────────────
    log("3/5 Consultando eventos Purchase no pixel (últimos 730 dias)...")
    # Descobrir pixel ID da conta (o que tem dados: 2522706667879355)
    pixel_ids = set()
    for a in detailed:
        pid = a.get("pixel_id")
        if pid:
            pixel_ids.add(pid)
    # Também listar pixels da conta
    px_list, _ = api("%s/adspixels" % ACCOUNT, {"fields": "id,name,last_fired_time"})
    for px in (px_list or {}).get("data", []):
        pixel_ids.add(px["id"])

    log("  Pixels a verificar: %s" % list(pixel_ids))

    pixel_events = {}
    for pid in pixel_ids:
        until_ts = int(datetime.now().timestamp())
        since_ts = int((datetime.now() - timedelta(days=730)).timestamp())
        # Stats por evento
        d2, e2 = api("%s/stats" % pid, {
            "start_time": since_ts,
            "end_time": until_ts,
            "aggregation": "event",
        })
        events_730 = []
        purchase_count_730 = 0
        if d2 and "data" in d2:
            for ev in d2["data"]:
                events_730.append({"event": ev.get("event"), "count": ev.get("count", 0)})
                if "purchase" in (ev.get("event") or "").lower():
                    purchase_count_730 += int(ev.get("count", 0))
        else:
            log("  ERRO stats pixel %s: %s" % (pid, e2 or d2))

        # Stats por evento — janela 180D para comparação
        since_180 = int((datetime.now() - timedelta(days=180)).timestamp())
        d3, e3 = api("%s/stats" % pid, {
            "start_time": since_180,
            "end_time": until_ts,
            "aggregation": "event",
        })
        purchase_count_180 = 0
        if d3 and "data" in d3:
            for ev in d3["data"]:
                if "purchase" in (ev.get("event") or "").lower():
                    purchase_count_180 += int(ev.get("count", 0))

        pixel_events[pid] = {
            "events_730d": events_730,
            "purchase_total_730d": purchase_count_730,
            "purchase_total_180d": purchase_count_180,
        }
        log("  Pixel %s | Purchase 730d: %s | Purchase 180d: %s" % (
            pid, purchase_count_730, purchase_count_180))
        time.sleep(0.3)

    result["pixel_events"] = pixel_events

    # ── 5. Comparar 730D vs 180D ─────────────────────────────────────────────
    log("4/5 Comparando configurações 730D vs 180D...")
    aud_730 = [a for a in detailed if "730" in (a.get("name") or "")]
    aud_180 = [a for a in detailed if "180" in (a.get("name") or "") and "purchase" in (a.get("name") or "").lower()]
    result["aud_730d"] = aud_730
    result["aud_180d"] = aud_180

    # ── 6. Verificar se audience tem pixel_id vinculado ao correto ───────────
    log("5/5 Verificando vínculo de pixel nas audiências...")
    PIXEL_ATIVO = "2522706667879355"  # "Spid cup-site" — confirmado no diagnóstico 07/07
    pixel_check = []
    for a in detailed:
        pid = a.get("pixel_id", "")
        status_ok = pid == PIXEL_ATIVO
        pixel_check.append({
            "id": a["id"],
            "name": a.get("name"),
            "pixel_id": pid,
            "pixel_correto": status_ok,
            "tamanho_lower": a.get("approximate_count_lower_bound"),
            "tamanho_upper": a.get("approximate_count_upper_bound"),
            "retention_days": a.get("retention_days"),
            "delivery_status": a.get("delivery_status"),
            "operation_status": a.get("operation_status"),
        })
        log("  %s | pixel=%s | correto=%s | tamanho=%s" % (
            a.get("name","?"), pid, status_ok,
            a.get("approximate_count_lower_bound","?")))

    result["pixel_check"] = pixel_check

    # Salvar
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    log("SALVO → %s" % OUT)

    # Resumo
    print("\n" + "="*70)
    print("DIAGNÓSTICO PURCHASE 730D")
    print("="*70)
    for p in pixel_check:
        sz = p.get("tamanho_lower")
        print("  %-40s | pixel_ok=%-5s | tamanho=%s | retention=%s" % (
            (p.get("name") or "?")[:40],
            p.get("pixel_correto"),
            sz if sz is not None else "?",
            p.get("retention_days","?")
        ))

    print("\nEventos Purchase no pixel (730d vs 180d):")
    for pid, ev in pixel_events.items():
        print("  Pixel %s: 730d=%s | 180d=%s" % (pid, ev["purchase_total_730d"], ev["purchase_total_180d"]))

    return result

if __name__ == "__main__":
    run()
