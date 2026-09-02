"""Coleta de métricas da Meta API — somente leitura, zero LLM.

Retorna dict com todas as métricas necessárias para os avaliadores.
Erros são silenciosos: campo fica vazio, sentinel loga e segue.
"""
import json
import os
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

SP_TZ = timezone(timedelta(hours=-3))
PURCHASE_TYPES = ("omni_purchase", "purchase", "offsite_conversion.fb_pixel_purchase")


def _load_env():
    path = os.path.expanduser("~/.adforge/.env")
    e = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                v = v.strip().strip('"').strip("'")
                e[k.strip()] = v
    except Exception:
        pass
    return e


def _get(url, params, timeout=30):
    full = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"User-Agent": "adforge-sentinel/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            body = {"error": str(e)}
        return body, "HTTP %s" % e.code
    except Exception as e:
        return None, str(e)


def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _roas(row):
    pr = row.get("purchase_roas")
    if pr:
        try:
            return _f(pr[0].get("value", 0))
        except Exception:
            pass
    sp = _f(row.get("spend"))
    val = 0.0
    for av in row.get("action_values", []):
        if av.get("action_type") in PURCHASE_TYPES:
            val += _f(av.get("value", 0))
    return (val / sp) if sp else 0.0


def collect_metrics():
    env = _load_env()
    acc = env.get("META_AD_ACCOUNT_ID", "").strip()
    if not acc.startswith("act_"):
        acc = "act_" + acc
    tok = env.get("META_ACCESS_TOKEN", "").strip()
    ver = env.get("META_API_VERSION", "v25.0").strip()
    base = "https://graph.facebook.com/%s" % ver

    now = datetime.now(SP_TZ)
    today = now.strftime("%Y-%m-%d")
    yest = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    d7 = (now - timedelta(days=7)).strftime("%Y-%m-%d")

    result = {
        "ok": True, "errors": [],
        "collected_at": now.isoformat(),
        "active_adsets": [],
        "account_today": {}, "account_yesterday": {},
        "ads_today": [], "ads_yesterday": [],
        "adset_freq_7d": [],
        "daily_budget_total": 0.0,
        "has_active_campaign": False,
    }

    # ── 1. Adsets ativos + insights de hoje ──────────────────────────────────
    data, err = _get("%s/%s/adsets" % (base, acc), {
        "access_token": tok,
        "fields": (
            "id,name,effective_status,"
            "insights.date_preset(today){impressions,spend,frequency}"
        ),
        "filtering": json.dumps([{
            "field": "effective_status", "operator": "IN",
            "value": ["ACTIVE"]
        }]),
        "limit": 100,
    })
    if err:
        result["errors"].append("adsets: %s" % err)
    else:
        for a in data.get("data", []):
            ins_list = (a.get("insights") or {}).get("data", [])
            ins = ins_list[0] if ins_list else {}
            result["active_adsets"].append({
                "id": a["id"],
                "name": a.get("name", ""),
                "impressions_today": int(_f(ins.get("impressions", 0))),
                "spend_today": _f(ins.get("spend", 0)),
                "frequency_today": _f(ins.get("frequency", 0)),
            })

    # ── 2. Insights de conta: hoje e ontem ───────────────────────────────────
    for key, since, until in [("today", today, today), ("yesterday", yest, yest)]:
        data, err = _get("%s/%s/insights" % (base, acc), {
            "access_token": tok,
            "fields": "spend,purchase_roas,impressions,action_values",
            "time_range": json.dumps({"since": since, "until": until}),
        })
        if err:
            result["errors"].append("account_%s: %s" % (key, err))
            result["account_%s" % key] = {"spend": 0.0, "roas": 0.0, "impressions": 0}
        else:
            rows = data.get("data", [])
            row = rows[0] if rows else {}
            result["account_%s" % key] = {
                "spend": _f(row.get("spend", 0)),
                "roas": _roas(row),
                "impressions": int(_f(row.get("impressions", 0))),
            }

    # ── 3. Anúncios ativos (nível criativo): hoje e ontem ────────────────────
    for key, since, until in [("today", today, today), ("yesterday", yest, yest)]:
        data, err = _get("%s/%s/ads" % (base, acc), {
            "access_token": tok,
            "fields": (
                "id,name,adset_id,"
                "insights.time_range({\"since\":\"%s\",\"until\":\"%s\"})"
                "{impressions,spend}" % (since, until)
            ),
            "filtering": json.dumps([{
                "field": "effective_status", "operator": "IN",
                "value": ["ACTIVE"]
            }]),
            "limit": 100,
        })
        if err:
            result["errors"].append("ads_%s: %s" % (key, err))
        else:
            for a in data.get("data", []):
                ins_list = (a.get("insights") or {}).get("data", [])
                ins = ins_list[0] if ins_list else {}
                result["ads_%s" % key].append({
                    "id": a["id"],
                    "name": a.get("name", ""),
                    "adset_id": a.get("adset_id", ""),
                    "impressions": int(_f(ins.get("impressions", 0))),
                    "spend": _f(ins.get("spend", 0)),
                })

    # ── 4. Frequência + ROAS 7d por adset ────────────────────────────────────
    data, err = _get("%s/%s/insights" % (base, acc), {
        "access_token": tok,
        "fields": "adset_id,adset_name,frequency,purchase_roas,spend",
        "level": "adset",
        "time_range": json.dumps({"since": d7, "until": today}),
        "limit": 100,
    })
    if err:
        result["errors"].append("freq_7d: %s" % err)
    else:
        for row in data.get("data", []):
            if _f(row.get("spend", 0)) <= 0:
                continue
            result["adset_freq_7d"].append({
                "id": row.get("adset_id", ""),
                "name": row.get("adset_name", ""),
                "frequency": _f(row.get("frequency", 0)),
                "roas": _roas(row),
                "spend": _f(row.get("spend", 0)),
            })

    # ── 5. Budget diário total (campanhas ativas) ─────────────────────────────
    data, err = _get("%s/%s/campaigns" % (base, acc), {
        "access_token": tok,
        "fields": "id,name,daily_budget,lifetime_budget,effective_status,stop_time",
        "filtering": json.dumps([{
            "field": "effective_status", "operator": "IN",
            "value": ["ACTIVE"]
        }]),
        "limit": 50,
    })
    if err:
        result["errors"].append("campaigns: %s" % err)
    else:
        total = 0.0
        for c in data.get("data", []):
            db = _f(c.get("daily_budget", 0)) / 100.0
            lb = _f(c.get("lifetime_budget", 0)) / 100.0
            if db > 0:
                total += db
            elif lb > 0:
                # Estimativa conservadora: lifetime / 30
                stop = c.get("stop_time")
                if stop:
                    try:
                        stop_dt = datetime.fromisoformat(stop.replace("+0000", "+00:00"))
                        days_left = max(1, (stop_dt - now.astimezone()).days)
                        total += lb / days_left
                    except Exception:
                        total += lb / 30.0
                else:
                    total += lb / 30.0
        result["daily_budget_total"] = total

    # ── Determina se há campanha ativa com gasto ──────────────────────────────
    result["has_active_campaign"] = (
        len(result["active_adsets"]) > 0
        and result["account_today"].get("spend", 0) > 0
    )

    return result
