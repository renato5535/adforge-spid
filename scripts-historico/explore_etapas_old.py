"""Descobre URLs das etapas para eventos históricos via ctrlEvento.php."""
import os, re, sys
sys.path.insert(0, os.path.expanduser("~/.adforge/daily_analyst"))
from common import load_env

env = load_env()
email = env.get("AGENDA_ESPORTIVA_EMAIL", "")
pwd   = env.get("AGENDA_ESPORTIVA_PASSWORD", "")

AUTH_URL    = "https://auth.agendaesportiva.com.br/login?legacy=true&returnTo=%2F"
CTRL_EVENTO = "https://agendaesportiva.com.br/admin/controller/evento/ctrlEvento.php"

# Eventos históricos relevantes (SPID Cup Ingressos/Visitantes)
TARGET_IDS = {"1861", "2074", "2661"}

from playwright.sync_api import sync_playwright

SHOTS = os.path.expanduser("~/.adforge/reports/screenshots")
os.makedirs(SHOTS, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context()
    page = ctx.new_page()
    page.set_default_timeout(60000)

    page.goto(AUTH_URL)
    page.wait_for_load_state("networkidle")
    page.fill('input[name="nm_login"]', email)
    page.fill('input[name="nm_senha"]', pwd)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    print("LOGIN OK")

    # Carregar página de eventos e inspecionar HTML bruto
    page.goto(CTRL_EVENTO)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    page.screenshot(path=os.path.join(SHOTS, "old-01-eventos.png"), full_page=True)

    html = page.content()

    # Extrair todos os links da página
    links = page.query_selector_all("a")
    print("\n=== TODOS OS LINKS DA PÁGINA ===")
    for a in links:
        href = a.get_attribute("href") or ""
        txt  = (a.inner_text() or "").strip()[:60]
        if href:
            print("  [%s] => %s" % (txt, href))

    # Extrair HTML em torno de cada ID de evento alvo
    for eid in TARGET_IDS:
        print("\n=== CONTEXTO HTML ao redor de id=%s ===" % eid)
        # Encontra o trecho do HTML próximo a esse ID
        idx = html.find(eid)
        while idx != -1:
            snippet = html[max(0, idx-200):idx+500]
            # Limpa para legibilidade
            snippet_clean = re.sub(r"<script[^>]*>.*?</script>", "", snippet, flags=re.DOTALL)
            snippet_clean = re.sub(r"\s+", " ", snippet_clean)
            print("  ...%s..." % snippet_clean[:600])
            idx = html.find(eid, idx + 1)

    # Tentar navegação direta para painel de evento específico
    for eid in TARGET_IDS:
        urls_to_try = [
            "https://agendaesportiva.com.br/admin/controller/painel/?ref=area-do-organizador&id_evento=" + eid,
            "https://agendaesportiva.com.br/admin/controller/eventoxetapa/ctrlEventoxetapa.php?id_evento=" + eid,
        ]
        for url in urls_to_try:
            captured = []
            page.on("response", lambda r: captured.append(r.url) if "resumo_etapa" in r.url or "eventoxetapa" in r.url else None)
            page.goto(url)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(4000)
            text = re.sub(r"<[^>]+>", " ", page.content())
            text = re.sub(r"\s+", " ", text).strip()
            print("\n=== GET %s ===" % url)
            print("  Texto (500):", text[:500])
            print("  APIs capturadas:", captured[:10])

    browser.close()
