"""Passo A — Coleta Meta (Marketing API), somente leitura.

Estratégia eficiente em chamadas: usa insights agregados em nível de conta por
'level' (campaign/adset/ad) e janela de tempo. Cada chamada traz todas as linhas
daquele nível numa página só (+ paginação), bem abaixo do teto de 50.

Janelas (timezone America/Sao_Paulo, UTC-3):
  - dia      = ontem (último dia completo)
  - prev     = anteontem (para variação)
  - d2 (48h) = ontem + anteontem
  - d7       = últimos 7 dias completos
"""
from datetime import timedelta
from common import http_get_json, ad_account, now_sp, f

GRAPH = "https://graph.facebook.com"
PURCHASE_TYPES = ("omni_purchase", "purchase", "offsite_conversion.fb_pixel_purchase")
INSIGHT_FIELDS = (
    "campaign_id,campaign_name,adset_id,adset_name,ad_id,ad_name,"
    "spend,impressions,clicks,ctr,frequency,actions,action_values,purchase_roas"
)


def _windows():
    today = now_sp().date()
    d = lambda x: x.isoformat()
    yest = today - timedelta(days=1)
    prev = today - timedelta(days=2)
    d3s  = today - timedelta(days=3)
    d7s  = today - timedelta(days=7)
    return {
        "day":  {"since": d(yest), "until": d(yest)},
        "prev": {"since": d(prev), "until": d(prev)},
        "d2":   {"since": d(prev), "until": d(yest)},
        "d3":   {"since": d(d3s),  "until": d(yest)},
        "d7":   {"since": d(d7s),  "until": d(yest)},
        "labels": {"day": d(yest), "prev": d(prev),
                   "d3_start": d(d3s), "d7_start": d(d7s), "d7_end": d(yest)},
    }


def _acted(items, key):
    if not items:
        return 0.0
    table = {a.get("action_type"): a.get("value") for a in items}
    for t in PURCHASE_TYPES:
        if t in table:
            return f(table[t])
    return 0.0


def purchases(row):
    return _acted(row.get("actions"), "actions")


def value(row):
    return _acted(row.get("action_values"), "action_values")


def roas(row):
    pr = row.get("purchase_roas")
    if pr:
        try:
            return f(pr[0].get("value"))
        except Exception:
            pass
    sp = f(row.get("spend"))
    return (value(row) / sp) if sp else 0.0


def _metrics(row):
    sp = f(row.get("spend"))
    pu = purchases(row)
    return {
        "spend": sp,
        "purchases": pu,
        "value": value(row),
        "roas": roas(row),
        "cpa": (sp / pu) if pu else 0.0,
        "ctr": f(row.get("ctr")),
        "freq": f(row.get("frequency")),
        "impressions": f(row.get("impressions")),
    }


def get_insights(token, ver, node, level, window, g, errors):
    """Busca insights paginados de `node` no `level`/`window`. Respeita guardrails."""
    rows = []
    url = "%s/%s/%s/insights" % (GRAPH, ver, node)
    params = {
        "level": level,
        "fields": INSIGHT_FIELDS,
        "time_range": '{"since":"%s","until":"%s"}' % (window["since"], window["until"]),
        "limit": "200",
        "access_token": token,
    }
    while url:
        if not g.api_ok():
            break
        data, err = http_get_json(url, params)
        g.count_api()
        params = None  # a URL de paginação já vem com tudo
        if err or (data and "error" in data):
            errors.append("insights %s/%s: %s" % (level, window["since"],
                          (data or {}).get("error", {}).get("message", err)))
            break
        rows.extend(data.get("data", []))
        url = (data.get("paging", {}) or {}).get("next")
    return rows


def get_account_balance(token, ver, account, g, errors):
    """Busca saldo pré-pago real da conta via funding_source_details.display_string.

    O campo `balance` da API não representa o saldo pré-pago — o valor correto
    está em funding_source_details.display_string (ex: 'Saldo disponível (R$2.371,52 BRL)').
    amount_spent é o gasto histórico total da conta (em centavos).
    """
    import re
    if not g.api_ok():
        return {}
    url = "%s/%s/%s" % (GRAPH, ver, account)
    params = {
        "fields": "funding_source_details,amount_spent,currency",
        "access_token": token,
    }
    data, err = http_get_json(url, params)
    g.count_api()
    if err or (data and "error" in data):
        errors.append("account_balance: %s" % (data or {}).get("error", {}).get("message", err))
        return {}
    balance = None
    display_string = None
    fsd = data.get("funding_source_details") or {}
    ds = fsd.get("display_string", "")
    if ds:
        display_string = ds
        m = re.search(r'R\$\s*([\d.]+,\d{2})', ds)
        if m:
            balance = f(m.group(1).replace(".", "").replace(",", "."))
    raw_spent = data.get("amount_spent")
    return {
        "currency": data.get("currency", "BRL"),
        "balance": balance,
        "display_string": display_string,
        "amount_spent": f(raw_spent) / 100.0 if raw_spent is not None else None,
    }


def get_active_ads(token, ver, account, g, errors):
    """Lista anúncios ATIVOS (estrutura) p/ detectar criativos com 0 entrega."""
    ads = {}
    url = "%s/%s/%s/ads" % (GRAPH, ver, account)
    params = {
        "fields": "id,name,adset_id,campaign_id,effective_status",
        "filtering": '[{"field":"effective_status","operator":"IN","value":["ACTIVE"]}]',
        "limit": "200",
        "access_token": token,
    }
    while url:
        if not g.api_ok():
            break
        data, err = http_get_json(url, params)
        g.count_api()
        params = None
        if err or (data and "error" in data):
            errors.append("ads ativos: %s" % (data or {}).get("error", {}).get("message", err))
            break
        for a in data.get("data", []):
            ads[a["id"]] = a
        url = (data.get("paging", {}) or {}).get("next")
    return ads


def _index(rows, id_key):
    out = {}
    for r in rows:
        out[r.get(id_key)] = r
    return out


def collect(env, g):
    """Coleta tudo do Meta e devolve estrutura normalizada para o analyzer."""
    token = env.get("META_ACCESS_TOKEN", "").strip()
    ver = env.get("META_API_VERSION", "v25.0").strip() or "v25.0"
    account = ad_account(env)
    win = _windows()
    errors = []

    data = {
        "ad_account": account,
        "window": win["labels"],
        "campaigns": [],
        "adsets": [],
        "ads": [],
        "totals": {},
        "errors": errors,
    }

    # 1) Campanhas — insights nível campanha (dia, prev, 3d, 7d)
    camp_day  = _index(get_insights(token, ver, account, "campaign", win["day"],  g, errors), "campaign_id")
    camp_prev = _index(get_insights(token, ver, account, "campaign", win["prev"], g, errors), "campaign_id")
    camp_d3   = _index(get_insights(token, ver, account, "campaign", win["d3"],   g, errors), "campaign_id")
    camp_d7   = _index(get_insights(token, ver, account, "campaign", win["d7"],   g, errors), "campaign_id")

    for cid, row in camp_day.items():
        m = _metrics(row)
        r3 = _metrics(camp_d3.get(cid, {})) if camp_d3.get(cid) else {}
        data["campaigns"].append({
            "id": cid, "name": row.get("campaign_name", cid), "status": "ACTIVE",
            "spend_24h": m["spend"], "purchases_24h": m["purchases"], "value_24h": m["value"],
            "roas_24h": m["roas"], "cpa_24h": m["cpa"], "ctr_24h": m["ctr"], "freq_24h": m["freq"],
            "spend_3d": r3.get("spend", 0), "purchases_3d": r3.get("purchases", 0),
            "value_3d": r3.get("value", 0),  "roas_3d": r3.get("roas", 0),
            "spend_7d": f(camp_d7.get(cid, {}).get("spend")),
        })

    # 2) Conjuntos — insights nível adset (dia, 48h p/ alerta ROAS, 7d p/ fadiga)
    adset_day = get_insights(token, ver, account, "adset", win["day"], g, errors)
    adset_d2 = _index(get_insights(token, ver, account, "adset", win["d2"], g, errors), "adset_id")
    adset_d7 = _index(get_insights(token, ver, account, "adset", win["d7"], g, errors), "adset_id")

    for row in adset_day:
        aid = row.get("adset_id")
        m = _metrics(row)
        data["adsets"].append({
            "id": aid, "name": row.get("adset_name", aid),
            "campaign_id": row.get("campaign_id"), "campaign_name": row.get("campaign_name"),
            "spend_24h": m["spend"], "purchases_24h": m["purchases"], "value_24h": m["value"],
            "roas_24h": m["roas"], "cpa_24h": m["cpa"], "ctr_24h": m["ctr"], "freq_24h": m["freq"],
            "roas_48h": roas(adset_d2.get(aid, {})),
            "freq_7d": f(adset_d7.get(aid, {}).get("frequency")),
        })

    # 3) Anúncios/criativos — insights nível ad (dia) + estrutura de ativos
    ad_day = get_insights(token, ver, account, "ad", win["day"], g, errors)
    active_ads = get_active_ads(token, ver, account, g, errors)
    delivered_ids = set()
    for row in ad_day:
        adid = row.get("ad_id")
        m = _metrics(row)
        if m["impressions"] > 0:
            delivered_ids.add(adid)
        data["ads"].append({
            "id": adid, "name": row.get("ad_name", adid),
            "adset_id": row.get("adset_id"), "adset_name": row.get("adset_name"),
            "campaign_id": row.get("campaign_id"),
            "spend_24h": m["spend"], "purchases_24h": m["purchases"], "value_24h": m["value"],
            "roas_24h": m["roas"], "ctr_24h": m["ctr"], "impressions_24h": m["impressions"],
            "active": adid in active_ads, "delivered_24h": m["impressions"] > 0,
        })

    # anúncios ATIVOS sem nenhuma entrega ontem (candidatos a substituição)
    # Restringe a campanhas com entrega real no período para excluir ads de campanhas
    # arquivadas/pausadas cujo effective_status ainda não propagou na API.
    active_campaign_ids = set(camp_day.keys())
    data["zero_delivery"] = [
        {"id": aid, "name": a.get("name", aid),
         "adset_id": a.get("adset_id"), "campaign_id": a.get("campaign_id")}
        for aid, a in active_ads.items()
        if aid not in delivered_ids and a.get("campaign_id") in active_campaign_ids
    ]

    # 4) Saldo da conta
    data["account_balance"] = get_account_balance(token, ver, account, g, errors)

    # 5) Totais
    tot = lambda lst, k: sum(f(x.get(k)) for x in lst)
    sp24  = tot(data["campaigns"], "spend_24h")
    val24 = tot(data["campaigns"], "value_24h")
    pu24  = tot(data["campaigns"], "purchases_24h")
    sp3   = tot(data["campaigns"], "spend_3d")
    val3  = tot(data["campaigns"], "value_3d")
    pu3   = tot(data["campaigns"], "purchases_3d")
    sp_prev  = sum(f(r.get("spend")) for r in camp_prev.values())
    val_prev = sum(value(r) for r in camp_prev.values())
    pu_prev  = sum(purchases(r) for r in camp_prev.values())
    data["totals"] = {
        "spend_24h": sp24,  "value_24h": val24,  "purchases_24h": pu24,
        "roas_24h":  (val24 / sp24)  if sp24 else 0.0,
        "spend_3d":  sp3,   "value_3d": val3,    "purchases_3d": pu3,
        "roas_3d":   (val3  / sp3)   if sp3  else 0.0,
        "spend_7d":  tot(data["campaigns"], "spend_7d"),
        "value_7d":  sum(value(r) for r in camp_d7.values()),
        "purchases_7d": sum(purchases(r) for r in camp_d7.values()),
        "roas_7d":   None,  # calculado abaixo
        "spend_prev": sp_prev, "value_prev": val_prev, "purchases_prev": pu_prev,
    }
    sp7 = data["totals"]["spend_7d"]
    val7 = data["totals"]["value_7d"]
    data["totals"]["roas_7d"] = (val7 / sp7) if sp7 else 0.0
    return data
