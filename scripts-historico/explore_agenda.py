"""Explora estrutura do Agenda Esportiva — Gerenciar Eventos."""
import os, sys, re, json
sys.path.insert(0, os.path.expanduser("~/.adforge/daily_analyst"))
from common import load_env
from playwright.sync_api import sync_playwright

env = load_env()
email = env.get("AGENDA_ESPORTIVA_EMAIL", "")
pwd   = env.get("AGENDA_ESPORTIVA_PASSWORD", "")

SHOTS = os.path.expanduser("~/.adforge/reports/screenshots")
os.makedirs(SHOTS, exist_ok=True)

AUTH_URL   = "https://auth.agendaesportiva.com.br/login?legacy=true&returnTo=%2F"
EVENTS_URL = "https://agendaesportiva.com.br/admin/controller/evento/ctrlEvento.php"
AREA_URL   = "https://agendaesportiva.com.br/admin/controller/painel/?ref=area-do-organizador"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context()
    page = ctx.new_page()
    page.set_default_timeout(60000)

    # Login
    page.goto(AUTH_URL)
    page.wait_for_load_state("networkidle")
    page.fill('input[name="nm_login"]', email)
    page.fill('input[name="nm_senha"]', pwd)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    print("LOGIN OK — URL:", page.url)

    # Painel principal — ver o menu
    page.goto(AREA_URL)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    page.screenshot(path=os.path.join(SHOTS, "harvest-00-painel.png"), full_page=True)

    # Todos os links do menu/nav
    links = page.query_selector_all("a")
    print("\n=== LINKS DO PAINEL ===")
    for a in links:
        href = a.get_attribute("href") or ""
        txt  = (a.inner_text() or "").strip()[:50]
        if href and ("evento" in href.lower() or "gerenci" in txt.lower() or "meu" in txt.lower()):
            print("  [%s] => %s" % (txt, href))

    # Página de gerenciar eventos
    page.goto(EVENTS_URL)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    page.screenshot(path=os.path.join(SHOTS, "harvest-01-eventos.png"), full_page=True)
    print("\nURL eventos:", page.url)

    # Texto limpo (5000 chars)
    html = page.content()
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    print("\n=== TEXTO PÁGINA EVENTOS (5000) ===")
    print(text[:5000])

    # Links na página de eventos
    links2 = page.query_selector_all("a")
    print("\n=== LINKS PÁGINA EVENTOS ===")
    for a in links2[:60]:
        href = a.get_attribute("href") or ""
        txt  = (a.inner_text() or "").strip()[:50]
        if href:
            print("  [%s] => %s" % (txt, href))

    # IDs de eventos no HTML
    ids_found = re.findall(r'id_evento[=_/](\d+)', html)
    ids_found += re.findall(r'/evento/(\d+)', html)
    ids_found += re.findall(r'data-id["\s]*=[\s"]*(\d+)', html)
    print("\n=== IDs ENCONTRADOS NO HTML ===", list(set(ids_found)))

    browser.close()

print("\nScreenshots salvas em:", SHOTS)
