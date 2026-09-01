"""
Agenda Esportiva — Harvest eventos históricos (SPID Cup 2022/2023/2024 Visitantes).

Navega em ctrlEventoxetapa.php?id_evento={ID} para cada evento,
extrai todos os id_eventoxetapa e coleta resumo_etapa + vl_inscricoes.
Mescla com o agenda-historico.json existente.

Uso:
  python agenda_harvest_old.py
"""
import os, re, sys, json, time
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.adforge/daily_analyst"))
from common import load_env, ADFORGE_HOME

OUT_FILE  = os.path.join(ADFORGE_HOME, "reports", "agenda-historico.json")
CKPT_FILE = os.path.join(ADFORGE_HOME, "reports", "agenda-historico-old-checkpoint.json")

AUTH_URL      = "https://auth.agendaesportiva.com.br/login?legacy=true&returnTo=%2F"
CTRL_ETAPAS   = ("https://agendaesportiva.com.br/admin/controller/eventoxetapa/"
                 "ctrlEventoxetapa.php?id_evento=")
API_BASE      = "https://api.agendaoffroad.com.br"
RETIRADA_BASE = ("https://agendaesportiva.com.br/admin/controller/retirada_pagamento/"
                 "ctrlRetirada_pagamento.php?id_eventoxetapa=")

# Somente SPID Cup + SPID Fest Visitantes — Pilotos e NO PREP excluídos
TARGET_EVENTS = [
    {"id": "2962", "nome": "INGRESSOS SPID CUP 2025"},
]

# IDs de evento (4 dígitos) para excluir ao fazer busca por 5-6 dígitos
KNOWN_EVENT_IDS = {"1675","1676","1861","2074","2237","2548","2660","2661",
                   "2832","2961","2962","2982","3331","3341","3356"}


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


def get_etapa_ids(page, event_id):
    """
    Extrai todos os id_eventoxetapa da página ctrlEventoxetapa.php?id_evento=ID.
    Estratégia: encontra números de 5-6 dígitos no HTML que aparecem em contexto
    de id_eventoxetapa (atributos data-href, links, etc.) ou simplesmente
    como primeiros tokens nas linhas da tabela.
    """
    url = CTRL_ETAPAS + event_id
    page.goto(url)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    html = page.content()

    # Debug: mostra texto limpo
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    log("  [DEBUG] Texto (600): %s" % text[:600])

    etapa_ids = []

    # Estratégia 1: atributo data-href com 5-6 dígitos (botões Etapas)
    for m in re.finditer(r'data-href=["\']?(\d{5,6})["\']?', html):
        eid = m.group(1)
        if eid not in etapa_ids and eid not in KNOWN_EVENT_IDS:
            etapa_ids.append(eid)

    # Estratégia 2: data-id-atleta + data-href pattern nos buttons
    for m in re.finditer(r'data-id-atleta=["\']?(\d*)["\']?\s+data-href=["\']?(\d{5,6})["\']?', html):
        eid = m.group(2)
        if eid not in etapa_ids and eid not in KNOWN_EVENT_IDS:
            etapa_ids.append(eid)

    # Estratégia 3: qualquer id_eventoxetapa= no HTML
    for m in re.finditer(r'id_eventoxetapa[=_](\d{5,6})', html):
        eid = m.group(1)
        if eid not in etapa_ids and eid not in KNOWN_EVENT_IDS:
            etapa_ids.append(eid)

    # Estratégia 4: padrão "TD>NNNNN<" (ID na primeira célula da tabela)
    for m in re.finditer(r'<td[^>]*>\s*(\d{5,6})\s*</td>', html, re.IGNORECASE):
        eid = m.group(1)
        if eid not in etapa_ids and eid not in KNOWN_EVENT_IDS:
            etapa_ids.append(eid)

    # Estratégia 5: números de 5-6 dígitos que aparecem após "Listagem Etapas" no texto
    m_listagem = re.search(r'Listagem Etapas(.+)', text[:3000])
    if m_listagem:
        after = m_listagem.group(1)
        for m in re.finditer(r'\b(\d{5,6})\b', after):
            eid = m.group(1)
            if eid not in etapa_ids and eid not in KNOWN_EVENT_IDS:
                etapa_ids.append(eid)

    log("  IDs extraídos: %s" % etapa_ids)
    return etapa_ids


def collect_stage(page, etapa_id):
    """Coleta resumo_etapa + vl_inscricoes para uma etapa."""
    record = {
        "id_eventoxetapa": etapa_id,
        "capturado_em":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status":          "erro",
    }

    # API resumo_etapa
    try:
        resp = page.request.get(
            "%s/eventoxetapa/%s/resumo_etapa" % (API_BASE, etapa_id),
            timeout=20000,
        )
        if resp.ok:
            d = resp.json()
            record.update({
                "nm_etapa":      d.get("nm_etapa"),
                "nr_pagos":      d.get("nr_pagos"),
                "nr_reservados": d.get("nr_reservados"),
                "vl_total":      d.get("vl_total"),
                "dt_etapa":      d.get("dt_etapa"),
                "id_evento":     str(d.get("id_evento") or ""),
                "status":        "ok",
            })
        else:
            record["erro_api"] = "HTTP %d" % resp.status
    except Exception as ex:
        record["erro_api"] = str(ex)[:80]

    # Valor de Inscrições
    try:
        pg2 = page.context.new_page()
        pg2.set_default_timeout(25000)
        pg2.goto(RETIRADA_BASE + etapa_id)
        pg2.wait_for_load_state("networkidle")
        pg2.wait_for_timeout(1000)
        record["vl_inscricoes"] = parse_vl_inscricoes(pg2.content())
        pg2.close()
    except Exception as ex:
        record["vl_inscricoes"] = None

    return record


def run():
    env   = load_env()
    email = env.get("AGENDA_ESPORTIVA_EMAIL", "")
    pwd   = env.get("AGENDA_ESPORTIVA_PASSWORD", "")
    if not email or not pwd:
        log("ERRO: credenciais ausentes")
        sys.exit(1)

    checkpoint = load_json(CKPT_FILE) or {"done_ids": [], "etapas": []}
    done_ids   = set(checkpoint.get("done_ids", []))
    new_etapas = list(checkpoint.get("etapas", []))

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("ERRO: Playwright não instalado")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx     = browser.new_context()
        page    = ctx.new_page()
        page.set_default_timeout(60000)

        # Login
        log("Login...")
        page.goto(AUTH_URL)
        page.wait_for_load_state("networkidle")
        page.fill('input[name="nm_login"]', email)
        page.fill('input[name="nm_senha"]', pwd)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        log("Login OK")

        for evt in TARGET_EVENTS:
            log("── %s (id=%s) ──" % (evt["nome"], evt["id"]))

            etapa_ids = get_etapa_ids(page, evt["id"])
            if not etapa_ids:
                log("  ⚠️ Nenhuma etapa extraída")
                continue

            for etid in etapa_ids:
                if etid in done_ids:
                    log("  ⏭️ Etapa %s já coletada" % etid)
                    continue

                log("  Coletando etapa %s..." % etid)
                record = collect_stage(page, etid)
                record["id_evento_pai"] = evt["id"]
                record["nm_evento_pai"] = evt["nome"]

                icon = "✅" if record["status"] == "ok" else "❌"
                log("  %s %s | pagos=%s | vl_inscricoes=%s" % (
                    icon,
                    (record.get("nm_etapa") or "?")[:40],
                    record.get("nr_pagos"),
                    record.get("vl_inscricoes"),
                ))

                new_etapas.append(record)
                done_ids.add(etid)
                save_json(CKPT_FILE, {"done_ids": list(done_ids), "etapas": new_etapas,
                                      "salvo_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                time.sleep(0.8)

        browser.close()

    # Mescla com arquivo principal
    existing     = load_json(OUT_FILE) or {"etapas": [], "event_map": {}}
    existing_ids = {e.get("id_eventoxetapa") for e in existing.get("etapas", [])}
    added = 0
    for et in new_etapas:
        if et.get("id_eventoxetapa") not in existing_ids:
            existing["etapas"].append(et)
            added += 1

    existing["gerado_em"]    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing["total_etapas"] = len(existing["etapas"])
    save_json(OUT_FILE, existing)
    log("Mesclado: +%d novas etapas → total %d" % (added, existing["total_etapas"]))

    if os.path.exists(CKPT_FILE):
        os.remove(CKPT_FILE)

    # Resumo — somente SPID Cup e SPID Fest Visitantes (exclui Pilotos, NO PREP, etc.)
    visitante_keywords = ("ingressos", "visitantes", "spid fest", "spid cup", "público")
    excluir_keywords   = ("pilotos", "no prep", "greatest show", "inscrição pilotos",
                          "inscrição de pilotos")

    def is_visitante(r):
        nm = (r.get("nm_etapa") or r.get("nm_evento_pai") or "").lower()
        return (any(k in nm for k in visitante_keywords) and
                not any(k in nm for k in excluir_keywords))

    print("\n" + "=" * 70)
    print("HISTÓRICO SPID Cup + SPID Fest — VISITANTES")
    print("=" * 70)
    relevant = sorted(
        [e for e in existing["etapas"] if is_visitante(e)],
        key=lambda x: x.get("dt_etapa") or ""
    )
    total_pagos = total_rec = 0
    for r in relevant:
        nm  = (r.get("nm_etapa") or r.get("nm_evento_pai") or "?")[:50]
        pg  = r.get("nr_pagos") or 0
        vl  = r.get("vl_inscricoes") or r.get("vl_total") or 0
        dt  = (r.get("dt_etapa") or "")[:10]
        total_pagos += pg if isinstance(pg, (int, float)) else 0
        total_rec   += vl if isinstance(vl, (int, float)) else 0
        print("  [%s] %-50s | %5d pagos | R$ %10.2f" % (dt, nm, pg, vl))
    print("-" * 70)
    print("  TOTAL: %d pagos | R$ %.2f" % (total_pagos, total_rec))
    print("\nArquivo completo: %s" % OUT_FILE)


if __name__ == "__main__":
    run()
