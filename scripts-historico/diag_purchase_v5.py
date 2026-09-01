"""Diagnóstico v5 — sem campo 'rule' no listing; consulta rule por ID individual."""
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
PIXEL_ATIVO = "2522706667879355"

def log(msg):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)

def api(ep, params=None):
    p = {"access_token": TOKEN}
    if params:
        p.update(params)
    url = ep if ep.startswith("http") else "%s/%s/%s" % (GRAPH, API_VER, ep)
    return http_get_json(url, p, timeout=25)

result = {"gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "conta": ACCOUNT}

# ── 1. Custom audiences sem 'rule' ────────────────────────────────────────────
log("1. Listando custom audiences (sem rule)...")
ca, err = api("%s/customaudiences" % ACCOUNT, {
    "fields": "id,name,approximate_count_lower_bound,approximate_count_upper_bound,"
              "subtype,retention_days,pixel_id,delivery_status,operation_status,time_created",
    "limit": "200"
})
if err or not ca or "data" not in ca:
    log("  AINDA ERRO: %s | %s" % (err, str(ca)[:300]))
    result["ca_error"] = str(err or ca)[:300]
    audiences = []
else:
    audiences = ca["data"]
    log("  Total: %d audiencias" % len(audiences))
    result["custom_audiences_list"] = audiences

    # Mostrar todas Purchase
    pur_auds = [a for a in audiences if "purchase" in (a.get("name") or "").lower()]
    log("\n  === AUDIENCIAS PURCHASE (%d) ===" % len(pur_auds))
    for a in pur_auds:
        lo = a.get("approximate_count_lower_bound")
        hi = a.get("approximate_count_upper_bound")
        pid = a.get("pixel_id", "SEM_PIXEL")
        log("  [%s] %-44s | sz=%s-%s | px=%s | ret=%sd | ok=%s" % (
            a["id"], a.get("name","?")[:44], lo, hi, pid,
            a.get("retention_days","?"), pid == PIXEL_ATIVO))

# ── 2. Consulta individual das audiences Purchase (com rule) ──────────────────
log("\n2. Detalhando cada Purchase audience individualmente...")
pur_auds = [a for a in audiences if "purchase" in (a.get("name") or "").lower()]
detailed = []
for a in pur_auds:
    aid = a["id"]
    d, e = api(aid, {
        "fields": "id,name,approximate_count_lower_bound,approximate_count_upper_bound,"
                  "retention_days,pixel_id,rule,subtype,delivery_status,operation_status"
    })
    if e or not d:
        log("  ERRO [%s]: %s" % (aid, e))
        detailed.append({"id": aid, "name": a.get("name"), "error": str(e)})
    else:
        # Parse rule
        rule_raw = d.get("rule") or "{}"
        try:
            d["rule_parsed"] = json.loads(rule_raw) if isinstance(rule_raw, str) else rule_raw
        except Exception:
            d["rule_parsed"] = {"raw": str(rule_raw)[:300]}
        detailed.append(d)
        lo = d.get("approximate_count_lower_bound")
        pid = d.get("pixel_id","?")
        log("  [%s] %-44s | sz=%s | px=%s | ok=%s" % (
            aid, d.get("name","?")[:44], lo, pid, pid == PIXEL_ATIVO))
        log("    rule: %s" % json.dumps(d.get("rule_parsed",{}))[:250])
    time.sleep(0.3)

result["purchase_audiences_detail"] = detailed

# ── 3. Comparação 730D vs 180D ────────────────────────────────────────────────
log("\n3. Comparando 730D vs 180D...")
aud_730 = next((a for a in detailed if "730" in (a.get("name") or "") and not a.get("error")), None)
aud_180 = next((a for a in detailed
                if "180" in (a.get("name") or "") and "purchase" in (a.get("name") or "").lower()
                and not a.get("error")), None)
result["aud_730d"] = aud_730
result["aud_180d"] = aud_180

hipoteses = []
if aud_730 and aud_180:
    px730 = aud_730.get("pixel_id","?")
    px180 = aud_180.get("pixel_id","?")
    sz730 = aud_730.get("approximate_count_lower_bound")
    sz180 = aud_180.get("approximate_count_lower_bound")
    r730  = aud_730.get("rule_parsed", {})
    r180  = aud_180.get("rule_parsed", {})

    log("  730D | pixel=%s | sz=%s | ok=%s" % (px730, sz730, px730 == PIXEL_ATIVO))
    log("  180D | pixel=%s | sz=%s | ok=%s" % (px180, sz180, px180 == PIXEL_ATIVO))

    if px730 != px180:
        hipoteses.append({
            "id": "H1", "prob": "ALTA",
            "titulo": "PIXEL INCORRETO na 730D",
            "detalhe": "730D -> pixel %s | 180D -> pixel %s | correto = %s" % (px730, px180, PIXEL_ATIVO),
            "acao": "Recriar audience [SITE] Purchase 730D apontando para pixel %s (Spid cup-site)" % PIXEL_ATIVO
        })
    elif px730 != PIXEL_ATIVO:
        hipoteses.append({
            "id": "H1b", "prob": "ALTA",
            "titulo": "AMBAS usam pixel incorreto",
            "detalhe": "730D e 180D -> pixel %s | correto = %s" % (px730, PIXEL_ATIVO),
            "acao": "Recriar ambas apontando para pixel %s" % PIXEL_ATIVO
        })
    else:
        # Mesmo pixel correto — comparar rules
        if sz730 is not None and (sz730 <= 0 or sz730 < 0):
            if r730 != r180:
                hipoteses.append({
                    "id": "H2", "prob": "MEDIA",
                    "titulo": "Rules diferentes entre 730D e 180D",
                    "detalhe": "730D rule: %s | 180D rule: %s" % (
                        json.dumps(r730)[:150], json.dumps(r180)[:150]),
                    "acao": "Verificar se evento de origem difere (omni_purchase vs purchase); recriar 730D com mesma rule da 180D"
                })
            else:
                hipoteses.append({
                    "id": "H3", "prob": "BAIXA",
                    "titulo": "Mesmo pixel, mesma rule, mas 730D vazia",
                    "detalhe": "Pode ser: audience recentemente recriada e ainda processando; ou abaixo do minimo de 100 pessoas",
                    "acao": "Aguardar 24-48h para Meta popular; ou verificar se audience foi deletada/recriada recentemente"
                })
        elif sz730 and sz730 > 0:
            hipoteses.append({
                "id": "OK", "prob": "N/A",
                "titulo": "730D NAO esta vazia (sz=%s)" % sz730,
                "detalhe": "A audience tem membros. O problema reportado pode ser de timing ou cache do Gerenciador.",
                "acao": "Verificar no Gerenciador de Publicos se o valor esta atualizado"
            })
elif not aud_730:
    hipoteses.append({
        "id": "H4", "prob": "INFO",
        "titulo": "Purchase 730D nao encontrada na lista de audiences",
        "detalhe": "Pode ter sido deletada. Lookalike baseado nela tambem seria invalido.",
        "acao": "Verificar no Gerenciador de Publicos se ainda existe"
    })

result["hipoteses"] = hipoteses

# ── 4. Info sobre Lookalike baseado em 730D ───────────────────────────────────
log("\n4. Lookalikes baseados em Purchase...")
lkl_auds = [a for a in audiences
             if a.get("subtype") == "LOOKALIKE" and "purchase" in (a.get("name") or "").lower()]
result["lookalike_purchase"] = lkl_auds
for a in lkl_auds:
    log("  LKL: [%s] %s | sz=%s" % (a["id"], a.get("name","?"), a.get("approximate_count_lower_bound")))

# Salvar
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
log("\nSalvo: %s" % OUT)

# Print final
print("\n" + "="*70)
print("RESUMO FINAL")
print("="*70)
print("\nPixel ativo: %s (Spid cup-site, criado 2022)" % PIXEL_ATIVO)
print("Pixel morto: 867066736318670 (Spid Cup, criado Jan/2026, nunca disparou)")
for h in hipoteses:
    print("\n[%s - %s] %s" % (h["id"], h["prob"], h["titulo"]))
    print("  %s" % h["detalhe"])
    print("  Acao: %s" % h["acao"])
