"""Avaliadores de condições — sem I/O, só lógica pura.

Cada avaliador recebe métricas + estado atual e retorna lista de condições ativas.
Estado de histerese é gerenciado aqui; debounce é aplicado no sentinel.py.
"""
from datetime import date, timedelta

# ── Configuração de fases ──────────────────────────────────────────────────────

EVENTS = [
    # (nome, data do evento)
    ("4ª Etapa",   date(2026, 10, 16)),
    ("SUPER FINAL", date(2026, 11, 19)),
]

# Thresholds por fase (de benchmarks_spid.md)
PHASE_THRESHOLDS = {
    "aquecimento": {"roas_min": 10.0, "roas_target": 15.0},
    "aceleracao":  {"roas_min": 8.0,  "roas_target": 12.0},
    "sprint":      {"roas_min": 5.0,  "roas_target": 8.0},
    "pre_campanha": {"roas_min": 0.0, "roas_target": 0.0},  # sem campanha ainda
}

# Histerese: ciclos consecutivos necessários para disparar
HYSTERESIS = {
    "zero_delivery":   6,   # 2h (6 × 20min)
    "roas_below_min":  9,   # 3h
    "overspend":       3,   # 1h
    "creative_loss":   9,   # 3h
    "freq_roas":       12,  # 4h
}

# Debounce: mínimo de horas entre re-alertas do mesmo tipo
DEBOUNCE_HOURS = {
    "zero_delivery":   4.0,
    "roas_below_min":  12.0,
    "overspend":       4.0,
    "creative_loss":   8.0,
    "freq_roas":       24.0,
}

# Frequência mínima por tipo de adset (por nome)
FREQ_THRESHOLDS = {
    "rmkt":       8.0,
    "lookalike":  6.0,
    "prospecto":  4.0,
}


def get_phase(today=None):
    """Retorna (fase_nome, min_roas, dias_ate_evento, nome_evento)."""
    if today is None:
        today = date.today()

    upcoming = [(n, d) for n, d in EVENTS if d >= today]
    if not upcoming:
        return "pre_campanha", 0.0, 999, "sem evento futuro"

    nome_evento, event_date = upcoming[0]
    days = (event_date - today).days

    if days > 14:
        fase = "aquecimento"
    elif days > 7:
        fase = "aceleracao"
    else:
        fase = "sprint"

    thresh = PHASE_THRESHOLDS[fase]
    return fase, thresh["roas_min"], days, nome_evento


def _update_consecutive(state, key, active):
    """Incrementa ou zera o contador de ciclos consecutivos para a condição."""
    cond = state["conditions"].setdefault(key, {
        "consecutive": 0, "first_seen": None, "last_alerted": None
    })
    if active:
        cond["consecutive"] += 1
        if cond["first_seen"] is None:
            cond["first_seen"] = _now_iso()
    else:
        cond["consecutive"] = 0
        cond["first_seen"] = None
    return cond["consecutive"]


def _now_iso():
    from datetime import datetime, timedelta, timezone
    return datetime.now(timezone(timedelta(hours=-3))).isoformat()


def eval_zero_delivery(adsets, state):
    """Detecta adsets ativos sem entrega hoje.

    Histerese: 6 ciclos consecutivos (2h).
    Loga adsets com 0 impressões apenas se a conta tiver algum gasto hoje
    (evita falso positivo antes da madrugada iniciar entregas).
    """
    results = []
    account_has_spend = any(a.get("spend_today", 0) > 0 for a in adsets)

    for a in adsets:
        key = "zero_delivery:%s" % a["id"]
        is_zero = (a.get("impressions_today", 0) == 0) and account_has_spend
        consec = _update_consecutive(state, key, is_zero)
        required = HYSTERESIS["zero_delivery"]
        results.append({
            "type": "zero_delivery",
            "key": key,
            "adset_id": a["id"],
            "adset_name": a["name"],
            "value": a.get("impressions_today", 0),
            "threshold": 1,
            "unit": "impressions",
            "consecutive": consec,
            "required": required,
            "triggered": consec >= required,
            "active": is_zero,
        })
    return results


def eval_roas(account_today, phase_min_roas, state):
    """Compara ROAS de conta com mínimo da fase.

    Histerese: 9 ciclos (3h). Ignora se spend==0 (sem campanha ativa).
    """
    key = "roas_below_min"
    roas = account_today.get("roas", 0.0)
    spend = account_today.get("spend", 0.0)

    is_below = (spend > 0) and (phase_min_roas > 0) and (roas < phase_min_roas)
    consec = _update_consecutive(state, key, is_below)
    required = HYSTERESIS["roas_below_min"]

    return {
        "type": "roas_below_min",
        "key": key,
        "value": roas,
        "threshold": phase_min_roas,
        "unit": "ROAS",
        "consecutive": consec,
        "required": required,
        "triggered": consec >= required,
        "active": is_below,
    }


def eval_overspend(account_today, daily_budget_total, state):
    """Detecta gasto diário acima de 130% do budget projetado.

    Histerese: 3 ciclos (1h). Ignora se budget==0.
    """
    key = "overspend"
    spend = account_today.get("spend", 0.0)

    if daily_budget_total <= 0:
        _update_consecutive(state, key, False)
        return {
            "type": "overspend", "key": key,
            "value": spend, "threshold": 0, "unit": "BRL",
            "consecutive": 0, "required": HYSTERESIS["overspend"],
            "triggered": False, "active": False,
            "note": "sem budget configurado",
        }

    pct = spend / daily_budget_total if daily_budget_total > 0 else 0
    is_over = pct > 1.30
    consec = _update_consecutive(state, key, is_over)
    required = HYSTERESIS["overspend"]

    return {
        "type": "overspend",
        "key": key,
        "value": spend,
        "threshold": daily_budget_total * 1.30,
        "unit": "BRL",
        "pct": pct,
        "consecutive": consec,
        "required": required,
        "triggered": consec >= required,
        "active": is_over,
    }


def eval_creative_loss(ads_today, ads_yesterday, state):
    """Detecta perda de entrega em anúncios ativos (queda >80% vs ontem).

    Compara impressions_today vs impressions_yesterday por anúncio.
    Só avalia se tiver dados de ontem e hoje.
    Histerese: 9 ciclos (3h).
    """
    results = []

    # Mapa id → impressions de ontem
    yest_map = {a["id"]: a.get("impressions", 0) for a in ads_yesterday}

    for a in ads_today:
        key = "creative_loss:%s" % a["id"]
        imp_today = a.get("impressions", 0)
        imp_yest = yest_map.get(a["id"], 0)

        if imp_yest < 100:
            # Base muito pequena: não conclui perda
            _update_consecutive(state, key, False)
            results.append({
                "type": "creative_loss", "key": key,
                "ad_id": a["id"], "ad_name": a["name"],
                "value": imp_today, "threshold": imp_yest * 0.20,
                "unit": "impressions",
                "consecutive": 0, "required": HYSTERESIS["creative_loss"],
                "triggered": False, "active": False,
                "note": "base insuficiente ontem (%d imp)" % imp_yest,
            })
            continue

        loss_pct = 1.0 - (imp_today / imp_yest) if imp_yest > 0 else 0.0
        is_losing = loss_pct > 0.80
        consec = _update_consecutive(state, key, is_losing)
        required = HYSTERESIS["creative_loss"]
        results.append({
            "type": "creative_loss",
            "key": key,
            "ad_id": a["id"],
            "ad_name": a["name"],
            "value": imp_today,
            "threshold": imp_yest * 0.20,
            "loss_pct": loss_pct,
            "unit": "impressions",
            "consecutive": consec,
            "required": required,
            "triggered": consec >= required,
            "active": is_losing,
        })
    return results


def eval_freq_roas(adset_freq_7d, state):
    """Detecta frequência alta + ROAS em queda (fadiga de audiência).

    Determina threshold de frequência pelo nome do adset:
    - contém 'rmkt' → 8.0
    - contém 'look' / 'looka' → 6.0
    - padrão (prospecto/frio) → 4.0
    Histerese: 12 ciclos (4h).
    """
    results = []

    for a in adset_freq_7d:
        key = "freq_roas:%s" % a["id"]
        name_lower = a["name"].lower()

        if "rmkt" in name_lower or "remarketing" in name_lower:
            freq_limit = FREQ_THRESHOLDS["rmkt"]
        elif "look" in name_lower:
            freq_limit = FREQ_THRESHOLDS["lookalike"]
        else:
            freq_limit = FREQ_THRESHOLDS["prospecto"]

        freq = a.get("frequency", 0.0)
        roas = a.get("roas", 0.0)
        spend = a.get("spend", 0.0)

        # Condição: freq acima do limite E ROAS abaixo de 3x (sinal de fadiga)
        is_fatigued = (spend > 0) and (freq > freq_limit) and (roas < 3.0)
        consec = _update_consecutive(state, key, is_fatigued)
        required = HYSTERESIS["freq_roas"]
        results.append({
            "type": "freq_roas",
            "key": key,
            "adset_id": a["id"],
            "adset_name": a["name"],
            "frequency": freq,
            "freq_limit": freq_limit,
            "roas": roas,
            "spend": spend,
            "consecutive": consec,
            "required": required,
            "triggered": consec >= required,
            "active": is_fatigued,
        })
    return results


def evaluate_all(metrics, state):
    """Executa todos os avaliadores e retorna lista consolidada de condições."""
    phase, roas_min, days_until, event_name = get_phase()

    conditions = []

    # 1. Zero delivery por adset
    conditions.extend(eval_zero_delivery(metrics.get("active_adsets", []), state))

    # 2. ROAS abaixo do mínimo da fase
    conditions.append(eval_roas(metrics.get("account_today", {}), roas_min, state))

    # 3. Overspend
    conditions.append(eval_overspend(
        metrics.get("account_today", {}),
        metrics.get("daily_budget_total", 0.0),
        state,
    ))

    # 4. Perda de entrega em criativos
    conditions.extend(eval_creative_loss(
        metrics.get("ads_today", []),
        metrics.get("ads_yesterday", []),
        state,
    ))

    # 5. Frequência + ROAS (fadiga)
    conditions.extend(eval_freq_roas(metrics.get("adset_freq_7d", []), state))

    return conditions, {
        "phase": phase,
        "roas_min": roas_min,
        "days_until_event": days_until,
        "event_name": event_name,
    }
