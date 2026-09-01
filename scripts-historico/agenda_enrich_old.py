"""
Enriquece as etapas históricas com nm_etapa, dt_etapa e nr_pagos.

Estratégias:
1. Nome + data: extrai da tabela em ctrlEventoxetapa.php
2. nr_pagos: tenta capturar via interceptação de resumo_etapa navegando
   no painel do evento (que dispara a API autenticada)
3. nr_pagos fallback: extrai do HTML da página de retirada (linha "Total Pago")
"""
import os, re, sys, json, time
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.adforge/daily_analyst"))
from common import load_env, ADFORGE_HOME

OUT_FILE    = os.path.join(ADFORGE_HOME, "reports", "agenda-historico.json")
AUTH_URL    = "https://auth.agendaesportiva.com.br/login?legacy=true&returnTo=%2F"
CTRL_ETAPAS = ("https://agendaesportiva.com.br/admin/controller/eventoxetapa/"
               "ctrlEventoxetapa.php?id_evento=")
RETIRADA    = ("https://agendaesportiva.com.br/admin/controller/retirada_pagamento/"
               "ctrlRetirada_pagamento.php?id_eventoxetapa=")
API_BASE    = "https://api.agendaoffroad.com.br"

TARGET_EVENTS = [
    {"id": "2962", "nome": "INGRESSOS SPID CUP 2025"},
]


def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), flush=True)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_nr_pagos_from_retirada(html):
    """Tenta extrair nr_pagos do HTML da página de retirada."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    # Padrões possíveis: "Total Pago 123", "Qtd Pago: 123", "Inscrições Pagas 123"
    patterns = [
        r'Total Pago[:\s]+(\d+)',
        r'Pag[oa]s?[:\s]+(\d+)',
        r'Inscrições Pagas[:\s]+(\d+)',
        r'Nr Pag[oa]s?[:\s]+(\d+)',
        r'Qtd\.?\s*Pag[oa]s?[:\s]+(\d+)',
        r'Confirmad[oa]s?[:\s]+(\d+)',
        r'(\d+)\s+pag[oa]',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def get_etapa_details_from_table(html, known_ids):
    """
    Extrai nome e data de cada etapa da tabela do ctrlEventoxetapa.
    A tabela tem padrão: ID | Nome | Cidade | Data | ...
    """
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    details = {}
    # Localiza cada ID conhecido e extrai nome + data
    for etid in known_ids:
        pattern = re.compile(
            re.escape(etid) + r'\s+'   # ID
            r'(.+?)'                    # Nome (lazy)
            r'\s+(?:Itatiba|São Paulo|Curitiba|SP)\s+'  # Cidade
            r'(\d{2}/\d{2}/\d{4})',    # Data
            re.IGNORECASE
        )
        m = pattern.search(text)
        if m:
            nome = m.group(1).strip()
            data = m.group(2)
            # Converte DD/MM/YYYY → YYYY-MM-DD
            try:
                d, mo, y = data.split("/")
                data_iso = "%s-%s-%s" % (y, mo, d)
            except Exception:
                data_iso = data
            details[etid] = {"nm_etapa": nome[:70], "dt_etapa": data_iso}

    return details


def run():
    env   = load_env()
    email = env.get("AGENDA_ESPORTIVA_EMAIL", "")
    pwd   = env.get("AGENDA_ESPORTIVA_PASSWORD", "")

    existing = load_json(OUT_FILE)
    etapas   = existing.get("etapas", [])

    target_ids = {evt["id"] for evt in TARGET_EVENTS}
    # Mapeia etapas históricas por id_eventoxetapa
    hist_etapas = {
        e["id_eventoxetapa"]: e
        for e in etapas
        if e.get("id_evento_pai") in target_ids
    }
    log("Etapas históricas a enriquecer: %d" % len(hist_etapas))

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("ERRO: Playwright")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx     = browser.new_context()
        page    = ctx.new_page()
        page.set_default_timeout(60000)

        # Login
        page.goto(AUTH_URL)
        page.wait_for_load_state("networkidle")
        page.fill('input[name="nm_login"]', email)
        page.fill('input[name="nm_senha"]', pwd)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        log("Login OK")

        for evt in TARGET_EVENTS:
            # IDs desta campanha
            ids_evt = [
                eid for eid, e in hist_etapas.items()
                if e.get("id_evento_pai") == evt["id"]
            ]
            log("── %s → %d etapas" % (evt["nome"], len(ids_evt)))

            # 1. Nomes e datas da tabela ctrlEventoxetapa
            page.goto(CTRL_ETAPAS + evt["id"])
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            html_table = page.content()
            details = get_etapa_details_from_table(html_table, ids_evt)
            log("  Nomes extraídos: %d/%d" % (len(details), len(ids_evt)))

            for etid in ids_evt:
                det = details.get(etid, {})
                if det.get("nm_etapa"):
                    hist_etapas[etid]["nm_etapa"] = det["nm_etapa"]
                if det.get("dt_etapa"):
                    hist_etapas[etid]["dt_etapa"] = det["dt_etapa"]

            # 2. nr_pagos: tenta interceptar resumo_etapa via painel do evento
            #    (o painel faz as chamadas autenticadas automaticamente)
            captured = {}

            def on_response(resp):
                m = re.search(r"eventoxetapa/(\d+)/resumo_etapa", resp.url)
                if m:
                    etid = m.group(1)
                    if etid in ids_evt and etid not in captured:
                        try:
                            captured[etid] = resp.json()
                        except Exception:
                            pass

            page.on("response", on_response)

            # Navega para cada etapa individualmente (o painel da etapa chama a API)
            for etid in ids_evt:
                # Tenta URL do painel com o evento específico
                painel_url = ("https://agendaesportiva.com.br/admin/controller/painel/"
                              "?ref=area-do-organizador&id_eventoxetapa=" + etid)
                page.goto(painel_url)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(3000)

                if etid in captured:
                    d = captured[etid]
                    if d.get("nr_pagos") is not None:
                        hist_etapas[etid]["nr_pagos"]      = d.get("nr_pagos")
                        hist_etapas[etid]["nr_reservados"] = d.get("nr_reservados")
                        hist_etapas[etid]["vl_total"]      = d.get("vl_total")
                        if not hist_etapas[etid].get("nm_etapa"):
                            hist_etapas[etid]["nm_etapa"] = d.get("nm_etapa")
                        log("  ✅ API etapa %s: pagos=%s" % (etid, d.get("nr_pagos")))
                        continue

                # Fallback: tenta extrair nr_pagos da página de retirada
                pg2 = page.context.new_page()
                pg2.set_default_timeout(20000)
                try:
                    pg2.goto(RETIRADA + etid)
                    pg2.wait_for_load_state("networkidle")
                    pg2.wait_for_timeout(1000)
                    html_ret = pg2.content()
                    nr = parse_nr_pagos_from_retirada(html_ret)
                    if nr is not None:
                        hist_etapas[etid]["nr_pagos"] = nr
                        log("  📄 Retirada etapa %s: pagos=%s" % (etid, nr))
                    else:
                        # Mostra trecho do HTML para debug
                        txt = re.sub(r"<[^>]+>", " ", html_ret)
                        txt = re.sub(r"\s+", " ", txt).strip()
                        log("  ❓ Etapa %s: nr_pagos não encontrado | texto: %s" % (etid, txt[:200]))
                except Exception as ex:
                    log("  ❌ Etapa %s retirada erro: %s" % (etid, str(ex)[:60]))
                finally:
                    pg2.close()
                time.sleep(0.5)

            try:
                page.remove_listener("response", on_response)
            except Exception:
                pass

        browser.close()

    # Atualiza o JSON com os dados enriquecidos
    for i, et in enumerate(etapas):
        etid = et.get("id_eventoxetapa")
        if etid in hist_etapas:
            etapas[i] = hist_etapas[etid]

    existing["etapas"]    = etapas
    existing["gerado_em"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_json(OUT_FILE, existing)
    log("JSON atualizado: %s" % OUT_FILE)

    # Relatório final — somente SPID Cup + SPID Fest Visitantes
    excluir = ("pilotos", "no prep", "inscrição pilotos", "greatest show",
               "inscrição de pilotos", "piloto")

    def is_visitante(r):
        nm = (r.get("nm_etapa") or r.get("nm_evento_pai") or "").lower()
        return not any(k in nm for k in excluir)

    print("\n" + "=" * 75)
    print("HISTÓRICO COMPLETO — SPID Cup + SPID Fest VISITANTES")
    print("=" * 75)
    relevant = sorted(
        [e for e in etapas if is_visitante(e)],
        key=lambda x: x.get("dt_etapa") or ""
    )
    total_pagos = total_rec = 0
    for r in relevant:
        nm  = (r.get("nm_etapa") or r.get("nm_evento_pai") or "?")[:52]
        pg  = r.get("nr_pagos") or 0
        vl  = r.get("vl_inscricoes") or r.get("vl_total") or 0
        dt  = (r.get("dt_etapa") or "")[:10]
        total_pagos += pg if isinstance(pg, (int, float)) else 0
        total_rec   += vl if isinstance(vl, (int, float)) else 0
        pg_str = str(int(pg)) if pg else "  ?"
        print("  [%s] %-52s | %5s pagos | R$ %10.2f" % (dt, nm, pg_str, vl))
    print("-" * 75)
    print("  TOTAL: %d pagos | R$ %.2f" % (total_pagos, total_rec))


if __name__ == "__main__":
    run()
