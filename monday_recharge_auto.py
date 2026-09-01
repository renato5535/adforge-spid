"""
monday_recharge_auto.py — Automação de Recarga Segunda-feira (24/Ago/2026)
==========================================================================
Roda a cada 30 min (agendado via Task Scheduler).
Quando detecta que o saldo subiu (recarga caiu na conta):
  1. Aumenta lifetime budget da campanha RMKT proporcionalmente
  2. Avalia PROSPECTO (ROAS 3d): se < threshold → pausa e migra budget para RMKT
  3. Notifica via Telegram
  4. Grava flag de execução para não repetir
"""
import os, sys, json, time, urllib.request, urllib.parse, urllib.error
from pathlib import Path
from datetime import date

# ── Config ────────────────────────────────────────────────────────────────────

CAMP_RMKT     = "120249601416320761"
CAMP_PROSP    = "120249601369080761"
PROSP_ROAS_THRESHOLD = 5.0    # abaixo disso → pausa PROSPECTO
SALDO_THRESHOLD      = 2000   # R$ — se saldo >= este valor, considera recarga detectada

FLAG_FILE = Path.home() / ".adforge" / "monday_recharge_done.flag"

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_env():
    for line in (Path.home() / ".adforge/.env").read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, _, v = s.partition("=")
            os.environ.setdefault(k.strip(), v.strip('"').strip("'"))

def _token(): return os.environ["META_ACCESS_TOKEN"]
def _base():  return f"https://graph.facebook.com/{os.environ.get('META_API_VERSION','v25.0')}"
def _acct():  return os.environ["META_AD_ACCOUNT_ID"]

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    log_path = Path.home() / ".adforge" / "logs" / "monday_recharge.log"
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def http_get(url, params=None):
    params = {**(params or {}), "access_token": _token()}
    try:
        with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params), timeout=20) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, json.loads(e.read()).get("error", {}).get("message", str(e))

def http_post(url, data):
    data = {**data, "access_token": _token()}
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, json.loads(e.read()).get("error", {}).get("message", str(e))

def telegram(env, msg):
    sys.path.insert(0, str(Path.home() / ".adforge" / "daily_analyst"))
    from telegram_send import send
    return send(env, msg)

# ── Funções principais ────────────────────────────────────────────────────────

def get_balance():
    """Retorna saldo pré-pago da conta em R$."""
    d, err = http_get(f"{_base()}/{_acct()}", {"fields": "funding_source_details"})
    if err or not d:
        return None
    fsd = d.get("funding_source_details", {})
    raw = fsd.get("amount", {})
    if isinstance(raw, dict):
        return float(raw.get("amount", 0)) / 100
    # Tentar extrair de display_string "R$ 1.234,56"
    ds = fsd.get("display_string", "")
    try:
        return float(ds.replace("R$","").replace(".","").replace(",",".").strip())
    except Exception:
        return None

def get_campaign_info(camp_id):
    """Retorna lifetime_budget (R$) e spend acumulado (R$) da campanha."""
    d, err = http_get(f"{_base()}/{camp_id}", {"fields": "lifetime_budget,name"})
    if err or not d:
        return None, None, None
    lifetime_cents = int(d.get("lifetime_budget", 0))
    name = d.get("name", "")

    ins, _ = http_get(f"{_base()}/{camp_id}/insights", {
        "fields": "spend", "date_preset": "lifetime",
    })
    spent = 0.0
    if ins and ins.get("data"):
        spent = float(ins["data"][0].get("spend", 0))

    return name, lifetime_cents / 100, spent

def get_prosp_roas_3d():
    """Retorna ROAS 3d da campanha PROSPECTO."""
    ins, err = http_get(f"{_base()}/{CAMP_PROSP}/insights", {
        "fields": "spend,action_values",
        "date_preset": "last_3d",
    })
    if err or not ins or not ins.get("data"):
        return None
    row = ins["data"][0]
    spend = float(row.get("spend", 0))
    if spend == 0:
        return 0.0
    vals = {a["action_type"]: float(a["value"]) for a in row.get("action_values", [])}
    rev  = vals.get("offsite_conversion.fb_pixel_purchase", 0)
    return round(rev / spend, 2)

def set_campaign_lifetime(camp_id, new_budget_reais):
    """Atualiza lifetime_budget da campanha (em R$)."""
    new_cents = int(new_budget_reais * 100)
    r, err = http_post(f"{_base()}/{camp_id}", {"lifetime_budget": new_cents})
    return err is None, err

def pause_campaign(camp_id):
    """Pausa uma campanha."""
    r, err = http_post(f"{_base()}/{camp_id}", {"status": "PAUSED"})
    return err is None, err

# ── Lógica principal ──────────────────────────────────────────────────────────

def run():
    load_env()
    env = {k: os.environ[k] for k in os.environ if k.startswith(("META_","TELEGRAM_"))}

    # Já executou hoje?
    if FLAG_FILE.exists():
        flag_date = FLAG_FILE.read_text().strip()
        if flag_date == str(date.today()):
            log("Recarga já processada hoje — nada a fazer.")
            return

    log("Verificando saldo da conta Meta...")
    saldo = get_balance()
    if saldo is None:
        log("ERRO: não foi possível obter saldo. Abortando.")
        return

    log(f"Saldo atual: R${saldo:.2f} | Threshold: R${SALDO_THRESHOLD}")

    if saldo < SALDO_THRESHOLD:
        log(f"Saldo abaixo de R${SALDO_THRESHOLD} — recarga ainda não detectada.")
        return

    # ── Recarga detectada ─────────────────────────────────────────────────────
    log(f"RECARGA DETECTADA! Saldo: R${saldo:.2f}")
    acoes = []

    # 1. Info da campanha RMKT
    rmkt_name, rmkt_lifetime, rmkt_spent = get_campaign_info(CAMP_RMKT)
    rmkt_remaining = rmkt_lifetime - rmkt_spent
    log(f"RMKT: lifetime=R${rmkt_lifetime:.0f} | gasto=R${rmkt_spent:.0f} | restante=R${rmkt_remaining:.0f}")

    # Novo lifetime = gasto atual + saldo disponível na conta
    # (saldo cobre os próximos dias; não excede o que o Meta pode usar)
    novo_rmkt_lifetime = rmkt_spent + saldo
    # Arredonda para cima em R$100
    novo_rmkt_lifetime = (int(novo_rmkt_lifetime / 100) + 1) * 100

    log(f"Aumentando RMKT lifetime: R${rmkt_lifetime:.0f} → R${novo_rmkt_lifetime:.0f}")
    ok, err = set_campaign_lifetime(CAMP_RMKT, novo_rmkt_lifetime)
    if ok:
        log(f"RMKT lifetime atualizado ✓")
        acoes.append(f"✅ RMKT lifetime: R${rmkt_lifetime:.0f} → R${novo_rmkt_lifetime:.0f}")
    else:
        log(f"RMKT ERRO: {err}")
        acoes.append(f"❌ RMKT lifetime ERRO: {err}")

    # 2. Avaliar PROSPECTO
    log("Avaliando PROSPECTO (ROAS 3d)...")
    prosp_roas = get_prosp_roas_3d()
    log(f"PROSPECTO ROAS 3d: {prosp_roas}x (threshold: {PROSP_ROAS_THRESHOLD}x)")

    prosp_name, prosp_lifetime, prosp_spent = get_campaign_info(CAMP_PROSP)
    prosp_remaining = prosp_lifetime - prosp_spent

    if prosp_roas is not None and prosp_roas < PROSP_ROAS_THRESHOLD:
        log(f"PROSPECTO abaixo do threshold ({prosp_roas}x < {PROSP_ROAS_THRESHOLD}x) — pausando...")
        ok2, err2 = pause_campaign(CAMP_PROSP)
        if ok2:
            log(f"PROSPECTO PAUSADA ✓ (restavam R${prosp_remaining:.0f} no budget)")
            acoes.append(f"⏸ PROSPECTO PAUSADA (ROAS 3d {prosp_roas}x < {PROSP_ROAS_THRESHOLD}x)")
            acoes.append(f"   Budget não utilizado: R${prosp_remaining:.0f} (lifetime foi fixado em R${prosp_lifetime:.0f})")

            # Redistribuir budget não usado da PROSPECTO para RMKT
            novo_rmkt_com_prosp = novo_rmkt_lifetime + prosp_remaining
            novo_rmkt_com_prosp = (int(novo_rmkt_com_prosp / 100) + 1) * 100
            log(f"Redistribuindo R${prosp_remaining:.0f} da PROSPECTO → RMKT (novo lifetime: R${novo_rmkt_com_prosp:.0f})")
            ok3, err3 = set_campaign_lifetime(CAMP_RMKT, novo_rmkt_com_prosp)
            if ok3:
                log(f"RMKT lifetime redistribuído ✓ → R${novo_rmkt_com_prosp:.0f}")
                acoes.append(f"✅ RMKT lifetime (com redistrib.): R${novo_rmkt_com_prosp:.0f}")
            else:
                log(f"RMKT redistrib ERRO: {err3}")
                acoes.append(f"❌ Redistrib RMKT ERRO: {err3}")
        else:
            log(f"PROSPECTO pausa ERRO: {err2}")
            acoes.append(f"❌ PROSPECTO pausa ERRO: {err2}")
    elif prosp_roas is None:
        log("PROSPECTO ROAS indisponível — mantendo ativa por precaução")
        acoes.append(f"⚠️ PROSPECTO: ROAS 3d indisponível — mantida ativa")
    else:
        log(f"PROSPECTO OK ({prosp_roas}x >= {PROSP_ROAS_THRESHOLD}x) — mantendo ativa")
        acoes.append(f"✅ PROSPECTO mantida ativa (ROAS 3d {prosp_roas}x)")

    # 3. Notificação Telegram
    msg = (
        f"🏁 AUTOMAÇÃO SEGUNDA-FEIRA — Recarga Detectada\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Saldo detectado: R${saldo:.2f}\n\n"
        f"Ações executadas:\n"
        + "\n".join(acoes) +
        f"\n\n⏰ {time.strftime('%d/%Ago %H:%M')}"
    )
    tg = telegram(env, msg)
    log(f"Telegram: {tg}")

    # 4. Gravar flag
    FLAG_FILE.write_text(str(date.today()))
    log("Flag gravada — automação concluída.")

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        run()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
