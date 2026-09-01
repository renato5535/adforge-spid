"""
Agenda Esportiva — Harvest histórico completo via interceptação do painel.

Estratégia:
  1. Login + navega para o painel do organizador
  2. Intercepta TODAS as chamadas resumo_etapa (carregadas automaticamente)
  3. Para cada etapa capturada, busca vl_inscricoes via ctrlRetirada_pagamento.php
  4. Salva tudo em agenda-historico.json com checkpoint incremental

Uso:
  python agenda_harvest.py            # coleta tudo
  python agenda_harvest.py --resume   # continua de onde parou

Saída: ~/.adforge/reports/agenda-historico.json
"""
import os, re, sys, json, time
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.adforge/daily_analyst"))
from common import load_env, ADFORGE_HOME

OUT_FILE  = os.path.join(ADFORGE_HOME, "reports", "agenda-historico.json")
CKPT_FILE = os.path.join(ADFORGE_HOME, "reports", "agenda-historico-checkpoint.json")
SHOTS_DIR = os.path.join(ADFORGE_HOME, "reports", "screenshots")

AUTH_URL      = "https://auth.agendaesportiva.com.br/login?legacy=true&returnTo=%2F"
PAINEL_URL    = "https://agendaesportiva.com.br/admin/controller/painel/?ref=area-do-organizador"
CTRL_EVENTO   = "https://agendaesportiva.com.br/admin/controller/evento/ctrlEvento.php"
API_BASE      = "https://api.agendaoffroad.com.br"
RETIRADA_BASE = ("https://agendaesportiva.com.br/admin/controller/retirada_pagamento/"
                 "ctrlRetirada_pagamento.php?id_eventoxetapa=")


def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), flush=True)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def parse_vl_inscricoes(html):
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    m = re.search(r"Valor de Inscri\S+\s+R\$\s*([\d.,]+)", text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(".", "").replace(",", "."))
    except Exception:
        return None


def get_event_map(page):
    """Retorna {id_evento: nome} extraído do ctrlEvento.php."""
    page.goto(CTRL_EVENTO)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)
    html  = page.content()
    text  = re.sub(r"<[^>]+>", " ", html)
    text  = re.sub(r"\s+", " ", text).strip()

    event_map = {}
    pattern = re.compile(
        r'\b(\d{4,5})\s+([A-Z][A-Z0-9 &\-]+?)\s+'
        r'(?=G3|Spid|Agenda|Big|\d{4,5}|$)'
    )
    for m in pattern.finditer(text):
        eid, ename = m.group(1), m.group(2).strip()
        if int(eid) < 10000:
            event_map[eid] = ename
    return event_map


def get_etapa_info(page, etapa_id):
    """Busca metadados de uma etapa via API."""
    try:
        resp = page.request.get(
            "%s/eventoxetapa/%s" % (API_BASE, etapa_id),
            timeout=15000,
        )
        if resp.ok:
            d = resp.json()
            return {
                "nm_etapa":    d.get("nm_etapa") or d.get("nome"),
                "dt_etapa":    d.get("dt_etapa") or d.get("data"),
                "id_evento":   str(d.get("id_evento") or ""),
                "nm_evento":   d.get("nm_evento") or "",
                "capacidade":  d.get("nr_vagas") or d.get("capacidade"),
            }
    except Exception:
        pass
    return {}


def collect_retirada(page, etapa_id):
    """Busca vl_inscricoes via ctrlRetirada_pagamento."""
    try:
        pg2 = page.context.new_page()
        pg2.set_default_timeout(25000)
        pg2.goto(RETIRADA_BASE + etapa_id)
        pg2.wait_for_load_state("networkidle")
        pg2.wait_for_timeout(1000)
        vl = parse_vl_inscricoes(pg2.content())
        pg2.close()
        return vl
    except Exception:
        return None


def run(resume=False):
    env   = load_env()
    email = env.get("AGENDA_ESPORTIVA_EMAIL", "")
    pwd   = env.get("AGENDA_ESPORTIVA_PASSWORD", "")
    if not email or not pwd:
        log("ERRO: credenciais ausentes no .env")
        sys.exit(1)

    checkpoint = load_json(CKPT_FILE) if (resume and os.path.exists(CKPT_FILE)) else None
    if checkpoint:
        done_ids    = set(checkpoint.get("done_ids", []))
        all_etapas  = checkpoint.get("etapas", [])
        log("RESUME — %d etapas já finalizadas" % len(done_ids))
    else:
        done_ids   = set()
        all_etapas = []

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("ERRO: Playwright não instalado")
        sys.exit(1)

    os.makedirs(SHOTS_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx     = browser.new_context()
        page    = ctx.new_page()
        page.set_default_timeout(60000)

        # ── 1. Login ──────────────────────────────────────────────────
        log("Login...")
        page.goto(AUTH_URL)
        page.wait_for_load_state("networkidle")
        page.fill('input[name="nm_login"]', email)
        page.fill('input[name="nm_senha"]', pwd)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        log("Login OK")

        # ── 2. Mapa de eventos ────────────────────────────────────────
        log("Carregando mapa de eventos...")
        event_map = get_event_map(page)
        log("  %d eventos encontrados: %s" % (len(event_map), list(event_map.keys())))

        # ── 3. Interceptar resumo_etapa no painel ─────────────────────
        captured = {}   # {etapa_id: dados_resumo}

        def on_response(response):
            url = response.url
            m = re.search(r"eventoxetapa/(\d+)/resumo_etapa", url)
            if m:
                etapa_id = m.group(1)
                if etapa_id not in done_ids:
                    try:
                        captured[etapa_id] = response.json()
                    except Exception:
                        captured[etapa_id] = None

        page.on("response", on_response)
        log("Carregando painel (interceptando chamadas de resumo_etapa)...")
        page.goto(PAINEL_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(6000)   # aguarda todas as chamadas assíncronas
        page.screenshot(path=os.path.join(SHOTS_DIR, "harvest-painel.png"))
        log("  Etapas capturadas via interceptação: %d" % len(captured))

        # ── 4. Para cada etapa capturada, enriquecer com dados ────────
        total = len(captured) + len(done_ids)
        for i, (etapa_id, resumo) in enumerate(captured.items()):
            pct = int((len(done_ids) + i) / max(total, 1) * 100)
            log("[%d%%] Etapa %s..." % (pct, etapa_id))

            record = {
                "id_eventoxetapa": etapa_id,
                "capturado_em":    datetime.now().strftime("%Y-%m-%d %H:%M"),
            }

            # Dados do resumo (interceptado)
            if resumo:
                record["nm_etapa"]      = resumo.get("nm_etapa")
                record["nr_pagos"]      = resumo.get("nr_pagos")
                record["nr_reservados"] = resumo.get("nr_reservados")
                record["vl_total"]      = resumo.get("vl_total")
                record["id_evento_raw"] = str(resumo.get("id_evento") or "")

            # Metadados completos da etapa via API
            info = get_etapa_info(page, etapa_id)
            record.update({k: v for k, v in info.items() if v is not None})

            # Mapeia nome do evento
            id_ev = record.get("id_evento_raw") or record.get("id_evento", "")
            record["nm_evento_mapa"] = event_map.get(id_ev, "")

            # Valor de Inscrições (retirada)
            log("  Buscando vl_inscricoes...")
            record["vl_inscricoes"] = collect_retirada(page, etapa_id)

            log("  → %s | pagos=%s | vl_inscricoes=%s" % (
                (record.get("nm_etapa") or "?")[:40],
                record.get("nr_pagos"),
                record.get("vl_inscricoes"),
            ))

            all_etapas.append(record)
            done_ids.add(etapa_id)

            # Checkpoint incremental
            save_json(CKPT_FILE, {
                "done_ids": list(done_ids),
                "etapas":   all_etapas,
                "salvo_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            time.sleep(0.5)

        browser.close()

    # ── 5. Resultado final ────────────────────────────────────────────
    final = {
        "gerado_em":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_etapas": len(all_etapas),
        "event_map":    event_map,
        "etapas":       all_etapas,
    }
    save_json(OUT_FILE, final)

    if os.path.exists(CKPT_FILE):
        os.remove(CKPT_FILE)

    # ── 6. Resumo impresso ────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("HARVEST CONCLUÍDO — %d etapas coletadas" % len(all_etapas))
    print("=" * 65)
    total_pagos = total_receita = 0
    for r in sorted(all_etapas, key=lambda x: x.get("dt_etapa") or ""):
        nm  = (r.get("nm_etapa") or r.get("nm_evento_mapa") or "?")[:45]
        pg  = r.get("nr_pagos") or 0
        vl  = r.get("vl_inscricoes") or r.get("vl_total") or 0
        dt  = (r.get("dt_etapa") or "")[:10]
        total_pagos   += pg if isinstance(pg, (int, float)) else 0
        total_receita += vl if isinstance(vl, (int, float)) else 0
        print("  [%s] %-45s | %4d pagos | R$ %10.2f" % (dt, nm, pg, vl))
    print("-" * 65)
    print("  TOTAIS: %d pagos | R$ %.2f receita acumulada" % (total_pagos, total_receita))
    print("\nArquivo: %s" % OUT_FILE)
    return final


if __name__ == "__main__":
    resume = "--resume" in sys.argv
    run(resume=resume)
