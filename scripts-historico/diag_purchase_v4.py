"""Diagnóstico v4 - corrige encoding; so custom audiences + pixel stats."""
import os, sys, json, time
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

sys.path.insert(0, os.path.expanduser("~/.adforge/daily_analyst"))
from common import load_env, http_get_json, ADFORGE_HOME

ENV      = load_env()
TOKEN    = ENV.get("META_ACCESS_TOKEN", "")
ACCOUNT  = ENV.get("META_AD_ACCOUNT_ID", "act_881694943239418")
API_VER  = ENV.get("META_API_VERSION", "v25.0")
GRAPH    = "https://graph.facebook.com"
OUT      = os.path.join(ADFORGE_HOME, "context", "diag_purchase_730d.json")

PIXEL_ATIVO = "2522706667879355"

def log(msg):
    # Encoding-safe print
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'), flush=True)

def api(endpoint, params=None):
    p = {"access_token": TOKEN}
    if params:
        p.update(params)
    url = endpoint if endpoint.startswith("http") else "%s/%s/%s" % (GRAPH, API_VER, endpoint)
    data, err = http_get_json(url, p, timeout=20)
    return data, err

result = {"gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "conta": ACCOUNT}

# ── 1. Pixels ─────────────────────────────────────────────────────────────────
log("1. Pixels...")
px_data, _ = api("%s/adspixels" % ACCOUNT, {"fields": "id,name,last_fired_time,creation_time"})
pixels = (px_data or {}).get("data", [])
result["pixels"] = pixels
for px in pixels:
    log("  [%s] %s | ultimo_disparo: %s | criado: %s" % (
        px["id"], px.get("name","?"),
        px.get("last_fired_time","nunca"), str(px.get("creation_time","?"))[:10]))

# ── 2. Purchase events por pixel (90d) ───────────────────────────────────────
log("2. Purchase events (90d)...")
pixel_stats = {}
for px in pixels:
    pid = px["id"]
    until_ts = int(datetime.now().timestamp())
    since_ts = int((datetime.now() - timedelta(days=90)).timestamp())
    d, e = api("%s/stats" % pid, {
        "start_time": since_ts, "end_time": until_ts, "aggregation": "event"
    })
    events = (d or {}).get("data", [])
    pur = [ev for ev in events if "purchase" in (ev.get("event") or "").lower()]
    pur_count = sum(int(x.get("count", 0)) for x in pur)
    # Tambem tenta com aggregation diferente para CAPI
    d2, e2 = api("%s/stats" % pid, {
        "start_time": since_ts, "end_time": until_ts, "aggregation": "event_source"
    })
    events2 = (d2 or {}).get("data", [])

    pixel_stats[pid] = {
        "name": px.get("name"),
        "event_count": len(events),
        "purchase_count_90d": pur_count,
        "all_event_names": [ev.get("event") for ev in events[:20]],
        "purchase_events_detail": pur,
        "event_source_data": events2[:10],
    }
    log("  Pixel %s (%s): %d tipos | Purchase 90d: %d | CAPI items: %d" % (
        pid, px.get("name","?"), len(events), pur_count, len(events2)))
    time.sleep(0.4)

result["pixel_stats"] = pixel_stats

# ── 3. Custom audiences ───────────────────────────────────────────────────────
log("3. Custom audiences...")
ca, ca_err = api("%s/customaudiences" % ACCOUNT, {
    "fields": "id,name,approximate_count_lower_bound,approximate_count_upper_bound,subtype,retention_days,pixel_id,rule,delivery_status,operation_status",
    "limit": "200"
})
if ca_err or not ca or "data" not in ca:
    log("  ERRO: %s | resp: %s" % (ca_err, str(ca)[:200]))
    result["ca_error"] = str(ca_err or ca)[:300]
else:
    audiences = ca["data"]
    log("  Total: %d audiencias" % len(audiences))

    # Parse rule JSON
    for a in audiences:
        rule_raw = a.get("rule") or "{}"
        try:
            a["rule_parsed"] = json.loads(rule_raw) if isinstance(rule_raw, str) else rule_raw
        except Exception:
            a["rule_parsed"] = {"raw": str(rule_raw)[:200]}

    result["custom_audiences"] = audiences

    pur_auds = [a for a in audiences if "purchase" in (a.get("name") or "").lower()]
    log("\n  === AUDIENCIAS PURCHASE ===")
    for a in pur_auds:
        lo = a.get("approximate_count_lower_bound")
        hi = a.get("approximate_count_upper_bound")
        pid = a.get("pixel_id", "SEM_PIXEL")
        ret = a.get("retention_days", "?")
        log("  [%s] %-42s sz=%s-%s px=%s ret=%sd px_ok=%s" % (
            a["id"], a.get("name","?")[:42], lo, hi, pid, ret, pid == PIXEL_ATIVO))

    # Comparar 730D vs 180D
    aud_730 = next((a for a in pur_auds if "730" in (a.get("name") or "")), None)
    aud_180 = next((a for a in pur_auds
                    if "180" in (a.get("name") or "") and "purchase" in (a.get("name") or "").lower()), None)

    result["aud_730d"] = aud_730
    result["aud_180d"] = aud_180

    log("\n  === COMPARACAO 730D vs 180D ===")
    if aud_730:
        log("  730D: pixel=%s | sz=%s | ret=%s" % (
            aud_730.get("pixel_id"), aud_730.get("approximate_count_lower_bound"),
            aud_730.get("retention_days")))
        log("  730D rule: %s" % json.dumps(aud_730.get("rule_parsed", {}))[:200])
    else:
        log("  730D: NAO ENCONTRADA via API")
    if aud_180:
        log("  180D: pixel=%s | sz=%s | ret=%s" % (
            aud_180.get("pixel_id"), aud_180.get("approximate_count_lower_bound"),
            aud_180.get("retention_days")))
        log("  180D rule: %s" % json.dumps(aud_180.get("rule_parsed", {}))[:200])
    else:
        log("  180D: NAO ENCONTRADA via API")

    # Hipoteses
    hipoteses = []
    if aud_730 and aud_180:
        px730 = aud_730.get("pixel_id","?")
        px180 = aud_180.get("pixel_id","?")
        sz730 = aud_730.get("approximate_count_lower_bound")
        sz180 = aud_180.get("approximate_count_lower_bound")
        if px730 != px180:
            hipoteses.append("H1-ALTA: PIXEL INCORRETO. 730D usa %s | 180D usa %s | correto=%s. Recriar 730D com pixel %s." % (
                px730, px180, PIXEL_ATIVO, PIXEL_ATIVO))
        elif px730 != PIXEL_ATIVO:
            hipoteses.append("H1b-ALTA: AMBAS usam pixel errado (%s). Correto seria %s." % (px730, PIXEL_ATIVO))
        elif sz730 is not None and sz730 <= 0 and sz180 and sz180 > 0:
            hipoteses.append("H2-MEDIA: mesmo pixel correto mas 730D vazia. Verificar rule JSON - evento de origem pode diferir.")
            hipoteses.append("H3-BAIXA: 730D abaixo do minimo Meta (<100 pessoas) - improvavel com 1200 compradores no FEST 2026.")
        elif sz730 and sz730 > 0:
            hipoteses.append("OK: 730D NAO esta vazia (sz=%s). Verificar se usuario ve o valor correto no Gerenciador." % sz730)
    elif not aud_730:
        hipoteses.append("INFO: 730D nao aparece na lista de /customaudiences. Pode ter sido deletada ou estar inativa.")

    result["hipoteses"] = hipoteses
    log("\n  === HIPOTESES ===")
    for h in hipoteses:
        log("  " + h)

# Salvar
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
log("\nSalvo: %s" % OUT)
