"""
AdForge @verifier — Anti-alucinação coletiva.

Papel: validar de forma independente as recomendações do daily-analyst
antes de qualquer ação ser enviada ao Renato. Sempre parte de dados
frescos da API — nunca de memória ou relatórios anteriores.

Gatilho: chamado pelo run.py do daily-analyst após gerar o relatório.
Saída: veredicto JSON + mensagem Telegram (se divergência crítica).
"""
import os
import sys
import json
import time
from pathlib import Path
from datetime import date, datetime, timedelta

# ── Carrega .env ─────────────────────────────────────────────────────────────
_env = Path.home() / ".adforge" / ".env"
for _line in _env.read_text(encoding="utf-8").splitlines():
    _line = _line.strip()
    if _line and not _line.startswith("#") and "=" in _line:
        k, _, v = _line.partition("=")
        os.environ.setdefault(k.strip(), v.strip("'\""))

import urllib.request
import urllib.parse
import urllib.error

TOKEN      = os.environ["META_ACCESS_TOKEN"]
AD_ACCOUNT = os.environ["META_AD_ACCOUNT_ID"]
TG_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT    = os.environ["TELEGRAM_CHAT_ID"]

# ── Config ────────────────────────────────────────────────────────────────────
MIN_SPEND_ACTIVE_USD   = 0.10   # adset "ativo" deve ter spend > isso hoje
ROAS_DIVERGENCE_PCT    = 30     # % de divergência entre ROAS real vs reportado que dispara alerta
MAX_ZERO_DELIVERY_ADS  = 3      # máx adsets "ativos" sem entrega antes de alertar

# ── HTTP helpers ──────────────────────────────────────────────────────────────
def _get(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode())

def meta_get(path, params):
    params["access_token"] = TOKEN
    qs = urllib.parse.urlencode(params)
    return _get(f"https://graph.facebook.com/v25.0/{path}?{qs}")

_LOCK_FILE = Path.home() / ".adforge" / "verifier" / ".last_sent"
_DEDUP_MINUTES = 5  # ignora disparo duplicado dentro deste intervalo

def _dedup_check() -> bool:
    """Retorna True se pode enviar (não enviou nos últimos DEDUP_MINUTES)."""
    if _LOCK_FILE.exists():
        try:
            last = datetime.fromisoformat(_LOCK_FILE.read_text().strip())
            if (datetime.now() - last).total_seconds() < _DEDUP_MINUTES * 60:
                print(f"[verifier] dedup — já enviado há menos de {_DEDUP_MINUTES}min, pulando")
                return False
        except Exception:
            pass
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOCK_FILE.write_text(datetime.now().isoformat())
    return True

def tg_send(msg):
    if not _dedup_check():
        return
    data = urllib.parse.urlencode({"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"}).encode()
    req  = urllib.request.Request(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data=data)
    urllib.request.urlopen(req, timeout=10)

# ── Verificações independentes ────────────────────────────────────────────────

def check_active_adsets():
    """Verifica se adsets marcados como ACTIVE têm entrega real (spend > 0 hoje)."""
    today = date.today().isoformat()
    data  = meta_get(f"{AD_ACCOUNT}/adsets", {
        "effective_status": json.dumps(["ACTIVE"]),
        "fields": "id,name,status,effective_status",
        "limit": 50,
    })
    adsets = data.get("data", [])

    # Pega insights de spend de hoje para cada adset
    zero_delivery = []
    for ads in adsets:
        ins = meta_get(f"{ads['id']}/insights", {
            "time_range": json.dumps({"since": today, "until": today}),
            "fields": "spend",
        })
        spend = float((ins.get("data") or [{}])[0].get("spend", 0))
        if spend < MIN_SPEND_ACTIVE_USD:
            zero_delivery.append({"id": ads["id"], "name": ads["name"], "spend_today": spend})

    return {"total_active": len(adsets), "zero_delivery": zero_delivery}

def check_account_spend():
    """Puxa spend real da conta hoje diretamente — sem depender do relatório anterior."""
    today = date.today().isoformat()
    ins   = meta_get(f"{AD_ACCOUNT}/insights", {
        "time_range": json.dumps({"since": today, "until": today}),
        "fields": "spend,purchase_roas,actions",
        "level": "account",
    })
    row = (ins.get("data") or [{}])[0]
    spend = float(row.get("spend", 0))
    roas_list = row.get("purchase_roas") or []
    roas = float(roas_list[0].get("value", 0)) if roas_list else 0.0
    purchases = sum(
        int(a.get("value", 0))
        for a in (row.get("actions") or [])
        if a.get("action_type") == "purchase"
    )
    return {"spend_today": spend, "roas_today": roas, "purchases_today": purchases}

# ── Veredicto ────────────────────────────────────────────────────────────────

def verify(reported: dict | None = None) -> dict:
    """
    Executa todas as verificações independentes.

    reported: dict opcional com o que o daily-analyst reportou
              (spend, roas, purchases) para comparação cruzada.

    Retorna dict com:
      - verdict: OK | WARN | ALERT
      - issues: lista de problemas encontrados
      - real_data: dados frescos da API
    """
    issues  = []
    ts      = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"[verifier] {ts} — iniciando verificação independente...")

    # 1. Dados reais da conta
    real = check_account_spend()
    print(f"[verifier] spend hoje: R${real['spend_today']:.2f} | ROAS: {real['roas_today']:.1f}x | compras: {real['purchases_today']}")

    # 2. Adsets ativos sem entrega
    delivery = check_active_adsets()
    zero = delivery["zero_delivery"]
    if len(zero) > MAX_ZERO_DELIVERY_ADS:
        issues.append({
            "severity": "WARN",
            "check": "zero_delivery",
            "msg": f"{len(zero)} adsets ativos sem entrega hoje: {[a['name'] for a in zero[:5]]}",
        })
        print(f"[verifier] WARN — {len(zero)} adsets ativos sem spend hoje")

    # 3. Divergência vs relatório anterior (se fornecido)
    if reported:
        rep_spend = float(reported.get("spend_today", 0))
        if rep_spend > 0:
            delta_pct = abs(real["spend_today"] - rep_spend) / rep_spend * 100
            if delta_pct > ROAS_DIVERGENCE_PCT:
                issues.append({
                    "severity": "ALERT",
                    "check": "spend_divergence",
                    "msg": f"Spend divergente: relatório={rep_spend:.2f} vs API agora={real['spend_today']:.2f} ({delta_pct:.0f}%)",
                })
                print(f"[verifier] ALERT — divergência de spend {delta_pct:.0f}%")

    # 4. Veredicto final
    severities = [i["severity"] for i in issues]
    if "ALERT" in severities:
        verdict = "ALERT"
    elif "WARN" in severities:
        verdict = "WARN"
    else:
        verdict = "OK"

    result = {
        "verdict": verdict,
        "timestamp": ts,
        "issues": issues,
        "real_data": {**real, **{"active_adsets": delivery["total_active"], "zero_delivery_count": len(zero)}},
    }

    # 5. Notificação Telegram se não-OK
    if verdict != "OK":
        emoji = "🚨" if verdict == "ALERT" else "⚠️"
        lines = [f"{emoji} <b>@verifier — {verdict}</b>", f"<i>{ts}</i>", ""]
        for issue in issues:
            lines.append(f"• {issue['msg']}")
        lines += ["", f"Dados reais: spend R${real['spend_today']:.2f} | ROAS {real['roas_today']:.1f}x | {real['purchases_today']} compras"]
        tg_send("\n".join(lines))
        print(f"[verifier] notificação Telegram enviada — {verdict}")

    print(f"[verifier] veredicto: {verdict} ({len(issues)} issues)")
    return result


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["verdict"] == "OK" else 1)
