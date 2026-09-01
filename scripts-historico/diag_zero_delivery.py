"""
Diagnóstico definitivo — Zero Delivery Meta Ads
3ª Etapa SPID Cup 2026 (zero entrega desde 18/Jul/2026)

Examina em profundidade:
  1. Status de pagamento/billing da conta (múltiplos campos)
  2. Status real de campanhas e adsets (delivery, flags)
  3. Tamanho real das audiences RMKT (abaixo de 1000 bloqueia entrega)
  4. Spend limits e caps de orçamento
  5. Flags de aprovação de anúncios
  6. Configuração de otimização dos adsets

Salva resultado em ~/.adforge/reports/diag_zero_delivery.json
"""
import os, sys, json, time
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.adforge/daily_analyst"))
from common import load_env, http_get_json, ADFORGE_HOME

ENV     = load_env()
TOKEN   = ENV.get("META_ACCESS_TOKEN", "")
ACCOUNT = ENV.get("META_AD_ACCOUNT_ID", "act_881694943239418")
API_VER = ENV.get("META_API_VERSION", "v25.0")
GRAPH   = "https://graph.facebook.com"
OUT     = os.path.join(ADFORGE_HOME, "reports", "diag_zero_delivery.json")

# IDs das campanhas da 3ª Etapa (obtidos em 18/Jul/2026)
CAMPANHA_PROSPECTO_NOME = "Prospecto"
CAMPANHA_RMKT_NOME      = "RMKT"


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
        p = None
        if err or not data:
            log("  ERRO paginação: %s" % (err or "sem dados"))
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
        "hipoteses": [],
        "veredicto": None,
        "acao_recomendada": None,
    }

    # ═══════════════════════════════════════════════════════════════
    # 1. STATUS COMPLETO DA CONTA (billing + flags)
    # ═══════════════════════════════════════════════════════════════
    log("\n── 1/6 Status completo da conta ──")
    acc_data, acc_err = api(ACCOUNT, {
        "fields": (
            "account_status,disable_reason,account_id,name,currency,"
            "funding_source_details,amount_spent,balance,"
            "spend_cap,daily_spend_limit,"
            "payment_account_id,is_prepay_account,"
            "owner,timezone_name,"
            "unsettled_balance,billing_events_fields"
        )
    })
    if acc_err or not acc_data:
        log("  ERRO ao buscar conta: %s" % acc_err)
        result["conta_status"] = {"erro": str(acc_err)}
    else:
        fsd = acc_data.get("funding_source_details") or {}
        result["conta_status"] = {
            "account_status":    acc_data.get("account_status"),
            "disable_reason":    acc_data.get("disable_reason"),
            "currency":          acc_data.get("currency"),
            "balance_api":       acc_data.get("balance"),          # pode ser CENTAVOS
            "amount_spent":      acc_data.get("amount_spent"),     # centavos histórico
            "spend_cap":         acc_data.get("spend_cap"),
            "daily_spend_limit": acc_data.get("daily_spend_limit"),
            "is_prepay":         acc_data.get("is_prepay_account"),
            "funding_display":   fsd.get("display_string"),        # saldo pré-pago real
            "funding_type":      fsd.get("type"),
            "funding_id":        fsd.get("id"),
            "unsettled":         acc_data.get("unsettled_balance"),
            "timezone":          acc_data.get("timezone_name"),
        }
        log("  account_status: %s | disable_reason: %s" % (
            acc_data.get("account_status"), acc_data.get("disable_reason")))
        log("  balance (API raw): %s | funding_display: %s" % (
            acc_data.get("balance"), fsd.get("display_string")))
        log("  spend_cap: %s | daily_spend_limit: %s" % (
            acc_data.get("spend_cap"), acc_data.get("daily_spend_limit")))
        log("  is_prepay: %s" % acc_data.get("is_prepay_account"))

    # ═══════════════════════════════════════════════════════════════
    # 2. CAMPANHAS — status + delivery + budget
    # ═══════════════════════════════════════════════════════════════
    log("\n── 2/6 Campanhas ──")
    campaigns = paginate(
        "%s/campaigns" % ACCOUNT,
        {
            "fields": (
                "id,name,status,effective_status,configured_status,"
                "daily_budget,lifetime_budget,budget_remaining,"
                "start_time,stop_time,spend_cap,"
                "delivery_info,issues_info,special_ad_categories"
            ),
            "filtering": '[{"field":"effective_status","operator":"IN",'
                         '"value":["ACTIVE","PAUSED","IN_PROCESS","WITH_ISSUES"]}]',
            "limit": "50",
        }
    )
    result["campanhas"] = []
    for c in campaigns:
        camp_info = {
            "id":                 c.get("id"),
            "name":               c.get("name"),
            "status":             c.get("status"),
            "effective_status":   c.get("effective_status"),
            "configured_status":  c.get("configured_status"),
            "daily_budget":       c.get("daily_budget"),      # centavos
            "budget_remaining":   c.get("budget_remaining"),  # centavos
            "spend_cap":          c.get("spend_cap"),
            "start_time":         c.get("start_time"),
            "delivery_info":      c.get("delivery_info"),
            "issues_info":        c.get("issues_info"),
            "special_ad_categories": c.get("special_ad_categories"),
        }
        result["campanhas"].append(camp_info)
        log("  [%s] %-30s | eff_status=%-15s | budget_remaining=%s | issues=%s" % (
            c.get("id"), (c.get("name") or "?")[:30],
            c.get("effective_status"), c.get("budget_remaining"),
            bool(c.get("issues_info"))))
    time.sleep(0.5)

    # ═══════════════════════════════════════════════════════════════
    # 3. ADSETS — status + delivery + targeting + budget
    # ═══════════════════════════════════════════════════════════════
    log("\n── 3/6 Adsets ──")
    adsets = paginate(
        "%s/adsets" % ACCOUNT,
        {
            "fields": (
                "id,name,status,effective_status,configured_status,"
                "campaign_id,optimization_goal,billing_event,"
                "daily_budget,lifetime_budget,budget_remaining,"
                "start_time,targeting,delivery_info,issues_info,"
                "promoted_object,bid_amount,bid_strategy"
            ),
            "filtering": '[{"field":"effective_status","operator":"IN",'
                         '"value":["ACTIVE","PAUSED","IN_PROCESS","WITH_ISSUES","CAMPAIGN_PAUSED"]}]',
            "limit": "50",
        }
    )
    result["adsets"] = []
    audience_ids_needed = set()
    for a in adsets:
        tgt = a.get("targeting") or {}
        custom_auds = tgt.get("custom_audiences", [])
        excl_auds   = tgt.get("exclusions", {}).get("custom_audiences", [])
        for ca in custom_auds + excl_auds:
            if ca.get("id"):
                audience_ids_needed.add(ca["id"])

        adset_info = {
            "id":               a.get("id"),
            "name":             a.get("name"),
            "campaign_id":      a.get("campaign_id"),
            "status":           a.get("status"),
            "effective_status": a.get("effective_status"),
            "optimization_goal":a.get("optimization_goal"),
            "billing_event":    a.get("billing_event"),
            "daily_budget":     a.get("daily_budget"),
            "budget_remaining": a.get("budget_remaining"),
            "bid_strategy":     a.get("bid_strategy"),
            "delivery_info":    a.get("delivery_info"),
            "issues_info":      a.get("issues_info"),
            "audience_ids":     [ca["id"] for ca in custom_auds],
            "excl_audience_ids":[ca["id"] for ca in excl_auds],
        }
        result["adsets"].append(adset_info)
        log("  [%s] %-35s | eff=%-15s | opt=%s | budget_rem=%s" % (
            a.get("id"), (a.get("name") or "?")[:35],
            a.get("effective_status"), a.get("optimization_goal"),
            a.get("budget_remaining")))
        if a.get("issues_info"):
            log("    ⚠️  ISSUES: %s" % a.get("issues_info"))
    time.sleep(0.5)

    # ═══════════════════════════════════════════════════════════════
    # 4. AUDIENCES — tamanho real (crítico para RMKT)
    # ═══════════════════════════════════════════════════════════════
    log("\n── 4/6 Audiences (todas as da conta) ──")
    all_auds = paginate(
        "%s/customaudiences" % ACCOUNT,
        {
            "fields": (
                "id,name,approximate_count_lower_bound,approximate_count_upper_bound,"
                "subtype,retention_days,delivery_status,operation_status,"
                "time_updated,lookalike_spec,pixel_id"
            ),
            "limit": "100",
        },
        max_pages=10,
    )
    result["audiences"] = []
    too_small = []
    for a in all_auds:
        lo = a.get("approximate_count_lower_bound") or 0
        hi = a.get("approximate_count_upper_bound") or 0
        delivery = (a.get("delivery_status") or {})
        delivery_code = delivery.get("code") if isinstance(delivery, dict) else delivery
        in_use = a["id"] in audience_ids_needed

        aud_info = {
            "id":              a.get("id"),
            "name":            a.get("name"),
            "subtype":         a.get("subtype"),
            "retention_days":  a.get("retention_days"),
            "size_lower":      lo,
            "size_upper":      hi,
            "delivery_status": delivery_code,
            "operation_status":a.get("operation_status"),
            "pixel_id":        a.get("pixel_id"),
            "in_use_by_adsets":in_use,
            "abaixo_do_minimo":lo < 1000 and lo > 0,
        }
        result["audiences"].append(aud_info)

        flag = " ⚠️ ABAIXO 1k" if (lo < 1000 and lo > 0) else ""
        uso = " [EM USO]" if in_use else ""
        log("  %-42s | sz: %s–%s | status: %s%s%s" % (
            (a.get("name") or "?")[:42], lo, hi, delivery_code, flag, uso))

        if lo < 1000 and lo > 0 and in_use:
            too_small.append(a.get("name"))
    time.sleep(0.5)

    # ═══════════════════════════════════════════════════════════════
    # 5. ADS — status + revisão
    # ═══════════════════════════════════════════════════════════════
    log("\n── 5/6 Ads (status e revisão) ──")
    ads = paginate(
        "%s/ads" % ACCOUNT,
        {
            "fields": (
                "id,name,status,effective_status,configured_status,"
                "adset_id,campaign_id,issues_info,"
                "review_feedback"
            ),
            "filtering": '[{"field":"effective_status","operator":"IN",'
                         '"value":["ACTIVE","PAUSED","PENDING_REVIEW","DISAPPROVED",'
                         '"IN_PROCESS","WITH_ISSUES"]}]',
            "limit": "200",
        }
    )
    result["ads"] = []
    ads_com_issue = []
    for a in ads:
        ad_info = {
            "id":               a.get("id"),
            "name":             a.get("name"),
            "adset_id":         a.get("adset_id"),
            "status":           a.get("status"),
            "effective_status": a.get("effective_status"),
            "issues_info":      a.get("issues_info"),
            "review_feedback":  a.get("review_feedback"),
        }
        result["ads"].append(ad_info)
        if a.get("issues_info") or a.get("effective_status") not in ("ACTIVE", "PAUSED"):
            ads_com_issue.append(ad_info)
            log("  ⚠️ [%s] %-35s | eff=%s | issues=%s" % (
                a.get("id"), (a.get("name") or "?")[:35],
                a.get("effective_status"), a.get("issues_info")))
    log("  Total ads: %d | com problemas: %d" % (len(ads), len(ads_com_issue)))
    time.sleep(0.5)

    # ═══════════════════════════════════════════════════════════════
    # 6. INSIGHTS ÚLTIMAS 48H — confirmar zero ou não
    # ═══════════════════════════════════════════════════════════════
    log("\n── 6/6 Insights últimas 48h (confirmar zero delivery) ──")
    from datetime import timedelta
    today = datetime.now().date()
    since = (today - timedelta(days=2)).isoformat()
    until = (today - timedelta(days=1)).isoformat()
    ins_data, ins_err = api(
        "%s/insights" % ACCOUNT,
        {
            "level": "account",
            "fields": "spend,impressions,clicks,actions",
            "time_range": '{"since":"%s","until":"%s"}' % (since, until),
        }
    )
    result["insights_48h"] = ins_data
    if ins_err:
        log("  ERRO insights: %s" % ins_err)
    else:
        rows = (ins_data or {}).get("data", [])
        if rows:
            r = rows[0]
            log("  Spend 48h: R$%s | Impressões: %s" % (r.get("spend"), r.get("impressions")))
        else:
            log("  Sem dados de insights — zero confirmado")

    # ═══════════════════════════════════════════════════════════════
    # ANÁLISE CONSOLIDADA
    # ═══════════════════════════════════════════════════════════════
    log("\n── ANÁLISE CONSOLIDADA ──")
    hipoteses = []
    acao_recomendada = []

    # H1: Saldo
    cs = result.get("conta_status", {})
    balance_display = cs.get("funding_display", "")
    balance_api_raw = cs.get("balance_api", "")
    if balance_display and "0,15" in balance_display:
        hipoteses.append(
            "H1 CONFIRMADA: Saldo exibido pelo Meta = R$0,15 — conta em estado de "
            "'entrega suspensa' por saldo mínimo. O crédito de R$2.300 (depositado ~20/Jul) "
            "pode ter sido creditado mas não 'desbloqueado' a entrega."
        )
        acao_recomendada.append(
            "AÇÃO H1: Contatar suporte HUMANO Meta com: (a) comprovante do depósito de "
            "R$2.300 em 20/Jul, (b) ID da conta, (c) 'conta em estado de entrega suspensa "
            "por saldo, sem alerta nem notificação, zero delivery há 5+ dias'."
        )
    elif balance_display:
        hipoteses.append("H1 DESCARTADA: Saldo exibido = '%s' (parece OK)" % balance_display)

    # H2: Spend cap ou daily limit
    if cs.get("spend_cap") and int(cs.get("spend_cap", "0")) > 0:
        hipoteses.append("H2 POSSÍVEL: Spend cap ativo na conta: %s centavos" % cs.get("spend_cap"))
        acao_recomendada.append("AÇÃO H2: Remover ou aumentar spend cap da conta no Gerenciador.")

    # H3: Audiences abaixo do mínimo (< 1000)
    if too_small:
        hipoteses.append(
            "H3 CONFIRMADA: Audiences ABAIXO DE 1000 PESSOAS em uso nos adsets: %s. "
            "O Meta bloqueia entrega de adsets com público-alvo menor que 1000." % ", ".join(too_small)
        )
        acao_recomendada.append(
            "AÇÃO H3: PAUSAR apenas os adsets que usam essas audiences pequenas "
            "(não deletar campanhas). Manter os demais adsets rodando."
        )

    # H4: Issues em adsets ou anúncios
    adsets_com_issue = [a for a in result["adsets"] if a.get("issues_info")]
    if adsets_com_issue:
        hipoteses.append(
            "H4 CONFIRMADA: %d adset(s) com issues reportadas: %s" % (
                len(adsets_com_issue),
                ", ".join(a["name"] for a in adsets_com_issue)
            )
        )
        acao_recomendada.append(
            "AÇÃO H4: Verificar e corrigir as issues nos adsets listados. "
            "Issues podem bloquear toda a campanha via efeito cascata."
        )

    if ads_com_issue:
        hipoteses.append(
            "H5 CONFIRMADA: %d anúncio(s) com status/issues inesperados." % len(ads_com_issue)
        )

    # Veredicto
    if not hipoteses:
        result["veredicto"] = (
            "Nenhuma hipótese confirmada automaticamente. "
            "Caso seja billing limbo, apenas suporte humano Meta resolve."
        )
    else:
        result["veredicto"] = " | ".join(hipoteses)

    result["hipoteses"] = hipoteses
    result["acao_recomendada"] = acao_recomendada
    result["audiences_abaixo_1k_em_uso"] = too_small
    result["adsets_com_issues"] = [a["name"] for a in adsets_com_issue]
    result["total_ads"] = len(ads)
    result["ads_com_problema"] = [a["name"] for a in ads_com_issue]

    # Salvar
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fout:
        json.dump(result, fout, ensure_ascii=False, indent=2, default=str)
    log("\nSALVO → %s" % OUT)

    # ── RELATÓRIO FINAL ─────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("DIAGNÓSTICO ZERO DELIVERY — 3ª ETAPA SPID CUP 2026")
    print("=" * 70)

    print("\n📊 CONTA:")
    print("  account_status  : %s" % cs.get("account_status"))
    print("  disable_reason  : %s" % cs.get("disable_reason"))
    print("  Saldo (display) : %s" % cs.get("funding_display"))
    print("  Saldo (API raw) : %s" % cs.get("balance_api"))
    print("  spend_cap       : %s" % cs.get("spend_cap"))
    print("  daily_limit     : %s" % cs.get("daily_spend_limit"))

    print("\n📦 ADSETS ATIVOS:")
    for a in result["adsets"]:
        print("  %-35s | eff=%-15s | opt=%-15s | issues=%s" % (
            (a["name"] or "?")[:35], a["effective_status"],
            a["optimization_goal"], bool(a.get("issues_info"))))

    print("\n👥 AUDIENCES EM USO (adsets ativos):")
    for a in result["audiences"]:
        if a["in_use_by_adsets"]:
            flag = " ⚠️ ABAIXO 1k" if a["abaixo_do_minimo"] else ""
            print("  %-42s | sz: %s–%s%s" % (
                (a["name"] or "?")[:42], a["size_lower"], a["size_upper"], flag))

    print("\n🚨 HIPÓTESES:")
    if hipoteses:
        for i, h in enumerate(hipoteses, 1):
            print("  %d. %s" % (i, h))
    else:
        print("  Nenhuma hipótese confirmada automaticamente")

    print("\n✅ AÇÕES RECOMENDADAS:")
    if acao_recomendada:
        for i, a in enumerate(acao_recomendada, 1):
            print("  %d. %s" % (i, a))
    else:
        print("  Ver veredicto acima")

    print("\n" + "=" * 70)
    return result


if __name__ == "__main__":
    run()
