"""
Diagnóstico v3 — consulta cirúrgica
1. Verifica token e permissões
2. Lista pixels da conta + stats de Purchase
3. Tenta /customaudiences com campos mínimos (mais chances de funcionar)
4. Busca apenas campanhas da SPID FEST 2026 e 3ª Etapa 2025 para extrair audience IDs
"""
import os, sys, json, time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.expanduser("~/.adforge/daily_analyst"))
from common import load_env, http_get_json, ADFORGE_HOME

ENV      = load_env()
TOKEN    = ENV.get("META_ACCESS_TOKEN", "")
ACCOUNT  = ENV.get("META_AD_ACCOUNT_ID", "act_881694943239418")
API_VER  = ENV.get("META_API_VERSION", "v25.0")
GRAPH    = "https://graph.facebook.com"
OUT      = os.path.join(ADFORGE_HOME, "context", "diag_purchase_730d.json")

PIXEL_ATIVO = "2522706667879355"
PIXEL_MORTO = "867066736318670"

def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), flush=True)

def api(endpoint, params=None):
    p = {"access_token": TOKEN}
    if params:
        p.update(params)
    url = endpoint if endpoint.startswith("http") else "%s/%s/%s" % (GRAPH, API_VER, endpoint)
    data, err = http_get_json(url, p, timeout=20)
    return data, err

result = {"gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "conta": ACCOUNT}

# ── 1. Pixels da conta ────────────────────────────────────────────────────────
log("1. Listando pixels...")
px_data, _ = api("%s/adspixels" % ACCOUNT, {
    "fields": "id,name,last_fired_time,creation_time"
})
pixels = (px_data or {}).get("data", [])
result["pixels"] = pixels
for px in pixels:
    log("  [%s] %-30s | último disparo: %s | criado: %s" % (
        px["id"], px.get("name","?"), px.get("last_fired_time","nunca"),
        str(px.get("creation_time","?"))[:10]))

# ── 2. Eventos Purchase em cada pixel (90d — janela segura para a API) ────────
log("2. Purchase events por pixel (últimos 90 dias)...")
pixel_stats = {}
for px in pixels:
    pid = px["id"]
    until_ts = int(datetime.now().timestamp())
    since_ts = int((datetime.now() - timedelta(days=90)).timestamp())
    d, e = api("%s/stats" % pid, {
        "start_time": since_ts, "end_time": until_ts, "aggregation": "event"
    })
    events = (d or {}).get("data", [])
    purchase_events = [ev for ev in events if "purchase" in (ev.get("event") or "").lower()]
    purchase_count = sum(int(e.get("count", 0)) for e in purchase_events)
    pixel_stats[pid] = {
        "name": px.get("name"),
        "total_events_types": len(events),
        "purchase_count_90d": purchase_count,
        "event_names": [ev.get("event") for ev in events],
        "error": str(e) if e else None,
    }
    log("  Pixel %s (%s): %d tipos de evento | Purchase 90d: %d | erro: %s" % (
        pid, px.get("name","?"), len(events), purchase_count, e or "nenhum"))
    time.sleep(0.5)

result["pixel_stats"] = pixel_stats

# ── 3. Custom audiences — tentativa com campos mínimos ───────────────────────
log("3. Custom audiences — campos mínimos...")
ca, ca_err = api("%s/customaudiences" % ACCOUNT, {
    "fields": "id,name,approximate_count_lower_bound,subtype,retention_days,pixel_id",
    "limit": "200"
})
if ca_err or not ca or "data" not in ca:
    log("  FALHOU (campos mínimos): %s | resp: %s" % (ca_err, str(ca)[:200]))
    result["custom_audiences_error"] = str(ca_err or ca)[:300]
else:
    audiences = ca["data"]
    log("  Encontradas: %d audiências" % len(audiences))
    result["custom_audiences"] = audiences
    purchase_auds = [a for a in audiences if "purchase" in (a.get("name") or "").lower()]
    log("  Purchase audiences: %d" % len(purchase_auds))
    for a in purchase_auds:
        lo = a.get("approximate_count_lower_bound")
        hi = a.get("approximate_count_upper_bound")
        pid = a.get("pixel_id", "SEM_PIXEL")
        log("  → [%s] %-40s | sz=%s–%s | px=%s | ret=%sd | pixel_ok=%s" % (
            a["id"], a.get("name","?")[:40], lo, hi, pid,
            a.get("retention_days","?"), pid == PIXEL_ATIVO))

# ── 4. Busca cirúrgica: últimas 5 campanhas com "SPID" no nome ────────────────
log("4. Campanhas SPID recentes (busca por nome)...")
camp_data, camp_err = api("%s/campaigns" % ACCOUNT, {
    "fields": "id,name,status",
    "limit": "50",
    "date_preset": "last_year",
})
if camp_err or not camp_data:
    log("  ERRO campanhas: %s" % camp_err)
else:
    all_camps = camp_data.get("data", [])
    # Filtra campanhas com SPID ou FEST no nome
    spid_camps = [c for c in all_camps
                  if any(k in (c.get("name") or "").upper() for k in ["SPID","FEST","ETAPA"])]
    log("  Campanhas SPID/FEST: %d de %d" % (len(spid_camps), len(all_camps)))

    audience_ids = {}
    for camp in spid_camps[:10]:  # máx 10 campanhas
        cid = camp["id"]
        ads_data, _ = api("%s/adsets" % cid, {
            "fields": "id,name,targeting",
            "limit": "30"
        })
        for adset in (ads_data or {}).get("data", []):
            tgt = adset.get("targeting", {})
            for key in ["custom_audiences", "excluded_custom_audiences"]:
                for aud in (tgt.get(key) or []):
                    aid = aud.get("id","")
                    aname = aud.get("name","")
                    if aid and aid not in audience_ids:
                        audience_ids[aid] = aname
        time.sleep(0.2)

    log("  Audience IDs únicos extraídos: %d" % len(audience_ids))
    result["audience_ids_from_spid_campaigns"] = audience_ids

    # Consulta direta para cada audience encontrada
    direct_auds = []
    for aid, aname in audience_ids.items():
        d, e = api(str(aid), {
            "fields": "id,name,approximate_count_lower_bound,approximate_count_upper_bound,"
                      "retention_days,pixel_id,rule,subtype,delivery_status,operation_status"
        })
        if e or not d:
            log("  ERRO [%s] %s: %s" % (aid, aname, e))
            direct_auds.append({"id": aid, "name": aname, "error": str(e)})
        else:
            rule_raw = d.get("rule") or "{}"
            try:
                rule_parsed = json.loads(rule_raw) if isinstance(rule_raw, str) else rule_raw
            except Exception:
                rule_parsed = {"raw": str(rule_raw)[:200]}
            d["rule_parsed"] = rule_parsed
            direct_auds.append(d)
            is_pur = "purchase" in (d.get("name") or "").lower()
            if is_pur:
                lo = d.get("approximate_count_lower_bound")
                pid = d.get("pixel_id","?")
                log("  🎯 [%s] %-40s | sz=%s | px=%s | px_ok=%s" % (
                    aid, d.get("name","?")[:40], lo, pid, pid == PIXEL_ATIVO))
        time.sleep(0.2)

    result["direct_audiences"] = direct_auds

# ── 5. Sumário e hipóteses ────────────────────────────────────────────────────
purchase_auds_all = []
for src in ["custom_audiences", "direct_audiences"]:
    for a in result.get(src, []):
        if "purchase" in (a.get("name") or "").lower() and a not in purchase_auds_all:
            purchase_auds_all.append(a)

aud_730 = next((a for a in purchase_auds_all if "730" in (a.get("name") or "")), None)
aud_180 = next((a for a in purchase_auds_all if "180" in (a.get("name") or "") and "purchase" in (a.get("name") or "").lower()), None)

print("\n" + "="*75)
print("DIAGNÓSTICO PURCHASE 730D — RESULTADO FINAL")
print("="*75)

print("\n[PIXELS]")
for pid, ps in pixel_stats.items():
    print("  %s (%s): Purchase 90d=%d | tipos_evento=%d | %s" % (
        pid, ps["name"], ps["purchase_count_90d"], ps["total_events_types"],
        "ATIVO" if ps["purchase_count_90d"] > 0 else "MORTO/SEM_PURCHASE"))

print("\n[AUDIÊNCIAS PURCHASE]")
for a in purchase_auds_all:
    lo = a.get("approximate_count_lower_bound")
    pid = a.get("pixel_id","?")
    print("  %-40s | sz=%s | px=%s | ret=%s | pixel_ok=%s" % (
        a.get("name","?")[:40], lo, pid,
        a.get("retention_days","?"), pid == PIXEL_ATIVO))

print("\n[HIPÓTESE PRINCIPAL]")
if aud_730 and aud_180:
    px730 = aud_730.get("pixel_id","?")
    px180 = aud_180.get("pixel_id","?")
    sz730 = aud_730.get("approximate_count_lower_bound")
    sz180 = aud_180.get("approximate_count_lower_bound")
    if px730 != px180:
        print("  H1 — PIXEL INCORRETO: 730D usa pixel %s | 180D usa pixel %s | ativo=%s" % (
            px730, px180, PIXEL_ATIVO))
        print("  AÇÃO: Recriar 730D apontando para o pixel %s (Spid cup-site)" % PIXEL_ATIVO)
    elif sz730 is not None and sz730 <= 0 and (sz180 or 0) > 0:
        print("  H2 — MESMO PIXEL mas 730D vazia. Verificar rule JSON das duas audiências.")
        print("  rule 730D:", json.dumps(aud_730.get("rule_parsed",{}))[:200])
        print("  rule 180D:", json.dumps(aud_180.get("rule_parsed",{}))[:200])
    else:
        print("  Ambas as audiências com mesmo pixel e tamanho similar — investigar rule.")
elif not aud_730:
    print("  Purchase 730D NÃO encontrada via API nos adsets SPID. Verificar manualmente no Gerenciador.")
else:
    print("  Dados parciais — ver arquivo JSON para detalhes completos.")

result["purchase_audiences_summary"] = purchase_auds_all
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
print("\nSalvo: %s" % OUT)
