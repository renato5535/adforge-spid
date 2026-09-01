"""
AdForge — Criação de campanhas Meta para 3ª Etapa SPID Cup 2026.

Estrutura:
  Campanha B — [RMKT][CONVERSÃO] 3ª Etapa SPID Cup 2026
    CJ B-00  Pageview 180D          (40% budget)
    CJ B-01  Video View 95% 180D
    CJ B-02  Purchase 180D
    CJ B-03  InitiateCheckout 90D   (exclui compradores)

  Campanha A — [PROSPECTO][CONVERSÃO] 3ª Etapa SPID Cup 2026
    CJ A-01  LKL 1% Purchase 180D
    CJ A-02  Engajamento 365D (MVP validado SPID FEST)

Budget Fase 1: B=R$80/dia  A=R$72/dia  Total=R$152/dia
Início: 2026-07-24
URL: https://agendaesportiva.com.br/ingressos_etapa3spidcup2026
Pixel: 2522706667879355
"""

import os, json, sys, urllib.request, urllib.parse, urllib.error
from pathlib import Path
from datetime import datetime, timezone

# ── carrega .env ───────────────────────────────────────────────────────────────
_env = Path.home() / ".adforge" / ".env"
for _line in _env.read_text(encoding="utf-8").splitlines():
    _line = _line.strip()
    if _line and not _line.startswith("#") and "=" in _line:
        k, _, v = _line.partition("=")
        os.environ.setdefault(k.strip(), v.strip("'\""))

TOKEN    = os.environ["META_ACCESS_TOKEN"]
ACCOUNT  = os.environ["META_AD_ACCOUNT_ID"]   # act_XXXXXXX
API_VER  = os.environ.get("META_API_VERSION", "v25.0")
BASE     = f"https://graph.facebook.com/{API_VER}"

PIXEL_ID = "2522706667879355"
DEST_URL = "https://agendaesportiva.com.br/ingressos_etapa3spidcup2026"

DRY_RUN = "--dry" in sys.argv   # python meta_create_campaigns_etapa3.py --dry


def _post(path, data):
    data["access_token"] = TOKEN
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(f"{BASE}/{path}", data=encoded, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        err = body.get("error", {})
        print(f"  ✗ ERRO HTTP {e.code}: {err.get('message')} (code={err.get('code')}, sub={err.get('error_subcode')})")
        print(f"    Detalhe: {err.get('error_user_msg', err.get('error_user_title', ''))}")
        print(f"    RAW: {json.dumps(err)[:400]}")
        return None


def _get(path, params=None):
    p = dict(params or {})
    p["access_token"] = TOKEN
    qs = urllib.parse.urlencode(p)
    with urllib.request.urlopen(f"{BASE}/{path}?{qs}", timeout=20) as r:
        return json.loads(r.read())


def create_campaign(name, daily_budget_cents, special_ad_categories=None):
    print(f"\n[CAMPANHA] Criando: {name}")
    data = {
        "name": name,
        "objective": "OUTCOME_SALES",
        "status": "PAUSED",
        "daily_budget": str(daily_budget_cents),
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        "special_ad_categories": json.dumps(special_ad_categories or []),
    }
    if DRY_RUN:
        print(f"  [DRY] {data}")
        return f"DRY_CAMPAIGN_{name[:8]}"
    result = _post(f"{ACCOUNT}/campaigns", data)
    if result and "id" in result:
        print(f"  ✓ ID: {result['id']}")
        return result["id"]
    return None


def create_adset(campaign_id, name, targeting, optimization_goal="OFFSITE_CONVERSIONS",
                 billing_event="IMPRESSIONS", promoted_object=None, excluded_custom_audiences=None):
    print(f"  [ADSET] Criando: {name}")

    # injeta exclusões dentro do targeting JSON
    t = dict(targeting)
    if excluded_custom_audiences:
        t["excluded_custom_audiences"] = excluded_custom_audiences

    data = {
        "campaign_id": campaign_id,
        "name": name,
        "status": "PAUSED",
        "optimization_goal": optimization_goal,
        "billing_event": billing_event,
        "targeting": json.dumps(t),
        "start_time": "2026-07-24T00:00:00-0300",
    }

    if promoted_object:
        data["promoted_object"] = json.dumps(promoted_object)

    if DRY_RUN:
        print(f"    [DRY] targeting_summary: {list(t.keys())}")
        return f"DRY_ADSET_{name[:8]}"
    result = _post(f"{ACCOUNT}/adsets", data)
    if result and "id" in result:
        print(f"    ✓ ID: {result['id']}")
        return result["id"]
    return None


# ── busca IDs de custom audiences pelo nome ────────────────────────────────────
def list_audiences():
    """Retorna dict {nome: id} de todas as custom audiences da conta."""
    result = _get(f"{ACCOUNT}/customaudiences", {"fields": "id,name", "limit": "200"})
    if not result:
        return {}
    return {a["name"]: a["id"] for a in result.get("data", [])}


def main():
    print("=" * 60)
    print("AdForge — Criação Campanhas 3ª Etapa SPID Cup 2026")
    print(f"Modo: {'DRY RUN (sem criar nada)' if DRY_RUN else 'LIVE'}")
    print("=" * 60)

    # ── mapeia audiences disponíveis ────────────────────────────────────────────
    print("\n[AUDIENCES] Mapeando custom audiences...")
    audiences = list_audiences() if not DRY_RUN else {}
    if audiences:
        for name in sorted(audiences):
            print(f"  · {name}: {audiences[name]}")
    else:
        print("  (DRY RUN — audiences não carregadas)")

    # IDs reais extraídos da conta em 18/Jul/2026
    AUD = {
        # Pageview
        "pageview_180d":       "23852023752760760",   # [SITE] PageView 180D
        # Video View 95% — usar os dois (FB + IG) no mesmo adset
        "vv_95_fb_180d":       "120212486259070761",  # FB - Video View 95% - 180D
        "vv_95_ig_180d":       "120210793604670761",  # IG Video View - 95% 180D
        # Purchase
        "purchase_180d":       "23852023749220760",   # [SITE] Purchase 180D
        # InitiateCheckout (melhor disponível: 180D)
        "ic_180d":             "120209063374030761",  # [SITE] Iniciate checkout - 180D
        # Engajamento 365D — usar FB + IG combinados
        "engaj_fb_365d":       "23851863652120760",   # FB - Envolvimento [TODOS] - 365D
        "engaj_ig_365d":       "23851863571880760",   # IG - Envolvimento [TODOS] - 365D
        # Lookalike Purchase
        "lkl_purchase_1pct":   "120243828865620761",  # Semelhante 1% Purchase
    }

    def aid(key):
        return {"id": AUD[key]}

    pageview_180d     = aid("pageview_180d")
    videoview_fb      = aid("vv_95_fb_180d")
    videoview_ig      = aid("vv_95_ig_180d")
    purchase_180d     = aid("purchase_180d")
    ic_180d           = aid("ic_180d")
    engaj_fb          = aid("engaj_fb_365d")
    engaj_ig          = aid("engaj_ig_365d")
    lkl_purchase_1pct = aid("lkl_purchase_1pct")

    # ── Exclusões comuns ────────────────────────────────────────────────────────
    excl_compradores = [{"id": purchase_180d["id"]}]
    excl_rmkt_total  = [
        {"id": pageview_180d["id"]},
        {"id": videoview_fb["id"]},
        {"id": videoview_ig["id"]},
        {"id": purchase_180d["id"]},
        {"id": ic_180d["id"]},
    ]

    # ── geo targeting BR ────────────────────────────────────────────────────────
    geo_br = {
        "geo_locations": {"countries": ["BR"]},
        "age_min": 18,
        "age_max": 65,
    }

    # ══════════════════════════════════════════════════════════════════════════════
    # CAMPANHA B — REMARKETING (já criada: 120249458187120761)
    # ══════════════════════════════════════════════════════════════════════════════
    camp_b_id = "120249458187120761"
    print(f"\n[CAMPANHA B] Usando existente: {camp_b_id}")

    if camp_b_id:
        promoted_pixel = {"pixel_id": PIXEL_ID, "custom_event_type": "PURCHASE"}

        # B-00 Pageview 180D (carro-chefe: 40% budget via CBO)
        targeting_b00 = {**geo_br, "custom_audiences": [{"id": pageview_180d["id"]}]}
        create_adset(
            camp_b_id, "B-00 Pageview 180D",
            targeting=targeting_b00,
            promoted_object=promoted_pixel,
            excluded_custom_audiences=excl_compradores,
        )

        # B-01 Video View 95% 180D — FB + IG combinados
        targeting_b01 = {**geo_br, "custom_audiences": [videoview_fb, videoview_ig]}
        create_adset(
            camp_b_id, "B-01 Video View 95% 180D",
            targeting=targeting_b01,
            promoted_object=promoted_pixel,
            excluded_custom_audiences=excl_compradores,
        )

        # B-02 Purchase 180D
        targeting_b02 = {**geo_br, "custom_audiences": [{"id": purchase_180d["id"]}]}
        create_adset(
            camp_b_id, "B-02 Purchase 180D",
            targeting=targeting_b02,
            promoted_object=promoted_pixel,
        )

        # B-03 InitiateCheckout 180D (exclui compradores)
        targeting_b03 = {**geo_br, "custom_audiences": [{"id": ic_180d["id"]}]}
        create_adset(
            camp_b_id, "B-03 InitiateCheckout 180D",
            targeting=targeting_b03,
            promoted_object=promoted_pixel,
            excluded_custom_audiences=excl_compradores,
        )

    # ══════════════════════════════════════════════════════════════════════════════
    # CAMPANHA A — PROSPECÇÃO (já criada: 120249458187670761)
    # ══════════════════════════════════════════════════════════════════════════════
    camp_a_id = "120249458187670761"
    print(f"\n[CAMPANHA A] Usando existente: {camp_a_id}")

    if camp_a_id:
        promoted_pixel = {"pixel_id": PIXEL_ID, "custom_event_type": "PURCHASE"}

        # A-01 LKL 1% Purchase (Semelhante 1% base compradores)
        targeting_a01 = {**geo_br, "custom_audiences": [{"id": lkl_purchase_1pct["id"]}]}
        create_adset(
            camp_a_id, "A-01 LKL 1% Purchase 180D",
            targeting=targeting_a01,
            promoted_object=promoted_pixel,
            excluded_custom_audiences=excl_rmkt_total,
        )

        # A-02 Engajamento 365D — FB + IG combinados (MVP SPID FEST)
        targeting_a02 = {**geo_br, "custom_audiences": [engaj_fb, engaj_ig]}
        create_adset(
            camp_a_id, "A-02 Engajamento 365D",
            targeting=targeting_a02,
            promoted_object=promoted_pixel,
            excluded_custom_audiences=excl_rmkt_total,
        )

    print("\n" + "=" * 60)
    print("PRÓXIMOS PASSOS:")
    print("  1. Verificar audiences acima — ajustar nomes se necessário")
    print("  2. Fazer upload dos 3 vídeos na Biblioteca de Ativos Meta")
    print("  3. Criar ads dentro de cada conjunto (via Gerenciador ou API)")
    print("  4. Ativar as campanhas em 24/Jul (mudar status PAUSED -> ACTIVE)")
    print("  URL destino:", DEST_URL)
    print("=" * 60)


if __name__ == "__main__":
    main()
