"""
Diagnóstico v2 — Purchase 730D vs 180D
Estratégia alternativa ao /customaudiences (retornou HTTP 500):
1. Extrai audience IDs a partir dos targeting_spec dos adsets recentes
2. Consulta cada audience diretamente por ID
3. Verifica eventos Purchase no pixel com janela menor (API /stats tem limite)
4. Tenta /business/customaudiences como alternativa
"""
import os, sys, json, time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.expanduser("~/.adforge/daily_analyst"))
from common import load_env, http_get_json, ADFORGE_HOME

ENV      = load_env()
TOKEN    = ENV.get("META_ACCESS_TOKEN", "")
ACCOUNT  = ENV.get("META_AD_ACCOUNT_ID", "act_881694943239418")
BIZ_ID   = ENV.get("META_BUSINESS_ID", "211395927795062")
API_VER  = ENV.get("META_API_VERSION", "v25.0")
GRAPH    = "https://graph.facebook.com"
OUT      = os.path.join(ADFORGE_HOME, "context", "diag_purchase_730d.json")

PIXEL_ATIVO = "2522706667879355"   # Spid cup-site (confirmado 07/07)
PIXEL_MORTO = "867066736318670"    # Spid Cup — nunca disparou

def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), flush=True)

def api(endpoint, params=None, base=None):
    p = {"access_token": TOKEN}
    if params:
        p.update(params)
    url = endpoint if endpoint.startswith("http") else "%s/%s/%s" % (GRAPH, API_VER, endpoint)
    data, err = http_get_json(url, p)
    return data, err

def paginate(endpoint, params, max_pages=8):
    p = {"access_token": TOKEN}
    if params:
        p.update(params)
    url = endpoint if endpoint.startswith("http") else "%s/%s/%s" % (GRAPH, API_VER, endpoint)
    results, pages = [], 0
    while url and pages < max_pages:
        data, err = http_get_json(url, p)
        p = None
        if err or not data:
            log("  PAGINAÇÃO ERRO: %s" % (err or "sem dados"))
            break
        results.extend(data.get("data", []))
        url = (data.get("paging", {}) or {}).get("next")
        pages += 1
        time.sleep(0.25)
    return results

result = {
    "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "conta": ACCOUNT,
    "hipoteses": [],
    "veredicto": None,
}

# ── A. Permissões do token ────────────────────────────────────────────────────
log("A. Verificando permissões e validade do token...")
me, err = api("me", {"fields": "id,name"})
if err or not me:
    log("  ERRO token: %s" % err)
    result["token_status"] = "ERRO: %s" % err
else:
    log("  Token OK: %s (%s)" % (me.get("name"), me.get("id")))
    result["token_status"] = "OK"

perms, _ = api("me/permissions")
if perms:
    granted = [p["permission"] for p in perms.get("data",[]) if p.get("status") == "granted"]
    log("  Permissões: %s" % ", ".join(granted))
    result["token_permissions"] = granted
    result["has_custom_audiences_perm"] = "custom_audiences" in granted or "ads_management" in granted
time.sleep(0.3)

# ── B. Tentar /business/customaudiences ───────────────────────────────────────
log("B. Tentando audiences via Business endpoint...")
biz_audiences, berr = api("%s/customaudiences" % BIZ_ID, {
    "fields": "id,name,approximate_count_lower_bound,approximate_count_upper_bound,retention_days,pixel_id,rule,subtype",
    "limit": "100"
})
if berr or not biz_audiences or "data" not in biz_audiences:
    log("  Business endpoint FALHOU: %s" % (berr or biz_audiences))
    result["biz_audiences_error"] = str(berr or biz_audiences)[:200]
else:
    biz_list = biz_audiences["data"]
    log("  Business audiences: %d" % len(biz_list))
    result["biz_audiences"] = biz_list
    for a in biz_list:
        if "purchase" in (a.get("name") or "").lower():
            log("    [%s] %s | tamanho: %s–%s | pixel: %s | retention: %s" % (
                a["id"], a.get("name"),
                a.get("approximate_count_lower_bound"),
                a.get("approximate_count_upper_bound"),
                a.get("pixel_id"), a.get("retention_days")))
time.sleep(0.3)

# ── C. Extrair audience IDs dos adsets recentes ────────────────────────────────
log("C. Extraindo audience IDs dos adsets dos últimos 90 dias...")
# Busca campanhas ativas/pausadas recentes
campaigns = paginate(
    "%s/campaigns" % ACCOUNT,
    {"fields": "id,name,status", "date_preset": "last_90d", "limit": "50"}
)
log("  Campanhas: %d" % len(campaigns))

audience_ids_found = {}
for camp in campaigns:
    cid = camp["id"]
    adsets = paginate(
        "%s/adsets" % cid,
        {"fields": "id,name,targeting,status", "limit": "50"}
    )
    for adset in adsets:
        targeting = adset.get("targeting", {})
        # custom_audiences pode estar em múltiplos campos
        for key in ["custom_audiences", "excluded_custom_audiences"]:
            for aud in (targeting.get(key) or []):
                aid = aud.get("id")
                aname = aud.get("name", "")
                if aid and aid not in audience_ids_found:
                    audience_ids_found[aid] = {"id": aid, "name": aname, "key": key}
    time.sleep(0.1)

log("  Audience IDs únicos encontrados nos adsets: %d" % len(audience_ids_found))
result["audience_ids_from_adsets"] = list(audience_ids_found.values())

# ── D. Consultar cada audience encontrada diretamente ─────────────────────────
log("D. Consultando detalhes de cada audience encontrada...")
detailed_audiences = []
for aid, info in audience_ids_found.items():
    d, err = api(str(aid), {
        "fields": "id,name,approximate_count_lower_bound,approximate_count_upper_bound,"
                  "retention_days,pixel_id,rule,subtype,delivery_status,operation_status,"
                  "data_source,time_created,time_updated"
    })
    if err or not d:
        log("  ERRO [%s] %s: %s" % (aid, info.get("name","?"), err))
        detailed_audiences.append({"id": aid, "name": info.get("name"), "erro": str(err)})
    else:
        rule_raw = d.get("rule", "{}")
        try:
            rule = json.loads(rule_raw) if isinstance(rule_raw, str) else rule_raw
        except Exception:
            rule = {"raw": str(rule_raw)[:300]}
        d["rule_parsed"] = rule
        detailed_audiences.append(d)

        lo = d.get("approximate_count_lower_bound", "?")
        hi = d.get("approximate_count_upper_bound", "?")
        pid = d.get("pixel_id", "?")
        name = d.get("name", "?")
        is_purchase = "purchase" in name.lower()
        marker = "🎯 PURCHASE" if is_purchase else "  "
        log("  %s [%s] %-45s | sz=%s–%s | px=%s | ret=%s" % (
            marker, aid, name[:45], lo, hi, pid, d.get("retention_days","?")))
    time.sleep(0.25)

result["detailed_audiences"] = detailed_audiences

# Filtrar as Purchase
purchase_auds = [a for a in detailed_audiences if "purchase" in (a.get("name") or "").lower()]
log("\n  AUDIÊNCIAS PURCHASE ENCONTRADAS: %d" % len(purchase_auds))
for a in purchase_auds:
    lo = a.get("approximate_count_lower_bound")
    hi = a.get("approximate_count_upper_bound")
    pid = a.get("pixel_id", "SEM PIXEL")
    log("    %s | tamanho=%s | pixel=%s | pixel_ok=%s" % (
        a.get("name"), "%s–%s" % (lo, hi), pid, pid == PIXEL_ATIVO))

result["purchase_audiences"] = purchase_auds

# ── E. Pixel events (janela 365d — limite mais seguro) ────────────────────────
log("\nE. Eventos Purchase nos 2 pixels (365d)...")
pixel_results = {}
for pid in [PIXEL_ATIVO, PIXEL_MORTO]:
    until_ts = int(datetime.now().timestamp())
    since_ts = int((datetime.now() - timedelta(days=365)).timestamp())
    d, e = api("%s/stats" % pid, {
        "start_time": since_ts, "end_time": until_ts, "aggregation": "event"
    })
    events = []
    purchase_count = 0
    if d and "data" in d:
        for ev in d["data"]:
            events.append(ev)
            if "purchase" in (ev.get("event") or "").lower():
                purchase_count += int(ev.get("count", 0))
    else:
        log("  ERRO stats px %s: %s" % (pid, e or d))
    pixel_results[pid] = {"events_365d": events, "purchase_365d": purchase_count}
    log("  Pixel %s: %d eventos únicos | Purchase 365d: %d" % (pid, len(events), purchase_count))
    time.sleep(0.3)

result["pixel_stats"] = pixel_results

# ── F. Hipóteses e Veredicto ──────────────────────────────────────────────────
log("\nF. Gerando diagnóstico...")

hipoteses = []

# H1: pixel errado na 730D
p730 = next((a for a in purchase_auds if "730" in (a.get("name") or "")), None)
p180 = next((a for a in purchase_auds if "180" in (a.get("name") or "") and "purchase" in (a.get("name") or "").lower()), None)

if p730 and p180:
    px730 = p730.get("pixel_id")
    px180 = p180.get("pixel_id")
    sz730_lo = p730.get("approximate_count_lower_bound")
    sz180_lo = p180.get("approximate_count_lower_bound")

    if px730 != px180:
        hipoteses.append({
            "id": "H1",
            "titulo": "PIXEL INCORRETO na audience 730D",
            "descricao": "Purchase 730D aponta para pixel %s; Purchase 180D aponta para pixel %s. O pixel ativo (Spid cup-site) é %s." % (px730, px180, PIXEL_ATIVO),
            "probabilidade": "ALTA",
            "evidencia": "Pixel 730D=%s vs 180D=%s vs ativo=%s" % (px730, px180, PIXEL_ATIVO),
            "correcao": "Recriar audience 730D apontando para pixel %s (Spid cup-site)" % PIXEL_ATIVO
        })
    elif sz730_lo is not None and (sz730_lo == 0 or sz730_lo < 0):
        hipoteses.append({
            "id": "H2",
            "titulo": "AUDIENCE 730D VAZIA — mesmo pixel correto",
            "descricao": "Ambas apontam para o mesmo pixel mas 730D tem tamanho zero. Possível: (a) regra de evento diferente na 730D, (b) abaixo do mínimo Meta (<100 pessoas), (c) recriada recentemente e ainda processando.",
            "probabilidade": "MÉDIA",
            "evidencia": "730D size=%s; 180D size=%s; mesmo pixel" % (sz730_lo, sz180_lo),
            "correcao": "Comparar rules JSON das duas audiences; verificar se evento de origem é o mesmo"
        })
elif p730 and not p180:
    hipoteses.append({
        "id": "H3",
        "titulo": "Purchase 730D encontrada mas 180D não nos adsets recentes",
        "descricao": "A 180D pode estar em campanhas mais antigas. Necessário consultar via gerenciador.",
        "probabilidade": "BAIXA",
        "evidencia": "730D nos adsets recentes, 180D não encontrada",
        "correcao": "Verificar no Gerenciador de Públicos manualmente"
    })

# H4: Token sem permissão para ver o tamanho real
if not result.get("has_custom_audiences_perm"):
    hipoteses.append({
        "id": "H4",
        "titulo": "TOKEN SEM PERMISSÃO ads_management / custom_audiences",
        "descricao": "O token do sistema user adforge-mcp pode não ter o scope custom_audiences, causando HTTP 500 no endpoint /customaudiences e possivelmente tamanho incorreto nas audiences individuais.",
        "probabilidade": "ALTA (causa do HTTP 500)",
        "evidencia": "HTTP 500 em /act_.../customaudiences; permissões visíveis: %s" % result.get("token_permissions", []),
        "correcao": "Adicionar permissão custom_audiences ao system user no Business Manager > Configurações do Sistema"
    })

# H5: Meta mínimo de 100 pessoas para estimativa
hipoteses.append({
    "id": "H5",
    "titulo": "AUDIENCE ABAIXO DO MÍNIMO META (<100 pessoas)",
    "descricao": "Meta não exibe estimativa de tamanho para audiences com menos de 100 membros. Se a 730D tem entre 1 e 99 pessoas, o tamanho aparece como 0 ou 'N/A' — mas a audience tecnicamente existe e pode ter membros.",
    "probabilidade": "BAIXA (improvável com ~1200 compradores no FEST 2026)",
    "evidencia": "1.200 ingressos no FEST 2026 + histórico de compras anteriores deveriam superar 100 facilmente",
    "correcao": "Verificar no Gerenciador de Públicos se aparece como 'Disponível' ou 'Não disponível'"
})

result["hipoteses"] = hipoteses

# Veredicto preliminar
if any(h["id"] == "H1" for h in hipoteses):
    result["veredicto"] = "PIXEL INCORRETO — H1 mais provável. Confirmar no Gerenciador de Públicos."
elif any(h["id"] == "H4" for h in hipoteses):
    result["veredicto"] = "PERMISSÃO DE TOKEN + possível pixel incorreto. Necessário acesso manual ao Gerenciador."
else:
    result["veredicto"] = "Dados insuficientes via API. Verificar manualmente no Gerenciador de Públicos Meta."

# Salvar
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=str)

# Print final
print("\n" + "="*70)
print("DIAGNÓSTICO PURCHASE 730D — RESUMO")
print("="*70)
print("Token: %s | Permissões ads_management: %s" % (
    result["token_status"], result.get("has_custom_audiences_perm")))
print("\nAudiências Purchase encontradas nos adsets:")
for a in purchase_auds:
    print("  %-40s | size=%s | pixel=%s | pixel_ok=%s" % (
        a.get("name","?")[:40],
        "%s–%s" % (a.get("approximate_count_lower_bound"), a.get("approximate_count_upper_bound")),
        a.get("pixel_id","?"),
        a.get("pixel_id") == PIXEL_ATIVO))
print("\nHipóteses:")
for h in hipoteses:
    print("  [%s] %s — %s" % (h["id"], h["titulo"], h["probabilidade"]))
print("\nVeredicto: %s" % result["veredicto"])
print("\nSalvo em: %s" % OUT)
