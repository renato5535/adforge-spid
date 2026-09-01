"""Investiga estrutura da página de etapas de um evento."""
import os, re, sys
sys.path.insert(0, os.path.expanduser("~/.adforge/daily_analyst"))
from common import load_env

env = load_env()
email = env.get("AGENDA_ESPORTIVA_EMAIL", "")
pwd   = env.get("AGENDA_ESPORTIVA_PASSWORD", "")

AUTH_URL = "https://auth.agendaesportiva.com.br/login?legacy=true&returnTo=%2F"

# Testar com INGRESSOS SPID CUP 2026 (id=3341) e com o atual SPID FEST (id_etapa=21688)
TEST_EVENT_ID = "3341"
CURRENT_ETAPA_ID = "21688"

from playwright.sync_api import sync_playwright

SHOTS = os.path.expanduser("~/.adforge/reports/screenshots")
os.makedirs(SHOTS, exist_ok=True)

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
    print("LOGIN OK")

    # 1. Tentar ctrlEventoXEtapa para evento 3341
    url1 = "https://agendaesportiva.com.br/admin/controller/eventoxetapa/ctrlEventoXEtapa.php?id_evento=" + TEST_EVENT_ID
    page.goto(url1)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    page.screenshot(path=os.path.join(SHOTS, "etapas-01.png"), full_page=True)
    html1 = page.content()

    text1 = re.sub(r"<script[^>]*>.*?</script>", "", html1, flags=re.DOTALL)
    text1 = re.sub(r"<style[^>]*>.*?</style>", "", text1, flags=re.DOTALL)
    text1 = re.sub(r"<[^>]+>", " ", text1)
    text1 = re.sub(r"\s+", " ", text1).strip()
    print("\n=== ctrlEventoXEtapa?id_evento=3341 (texto) ===")
    print(text1[:3000])
    print("\n=== IDs encontrados ===")
    print("eventoxetapa:", re.findall(r'eventoxetapa[=_/](\d+)', html1))
    print("id_etapa:", re.findall(r'id_etapa[=_](\d+)', html1))
    print("qualquer numero 5+ digitos:", list(set(re.findall(r'\b(\d{5,})\b', html1)))[:20])

    # 2. Tentar o painel com id_evento=3341
    url2 = "https://agendaesportiva.com.br/admin/controller/painel/?ref=area-do-organizador&id_evento=" + TEST_EVENT_ID
    captured_urls = []
    page.on("response", lambda r: captured_urls.append(r.url) if "api." in r.url else None)
    page.goto(url2)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(4000)
    page.screenshot(path=os.path.join(SHOTS, "etapas-02-painel.png"), full_page=True)
    print("\n=== URLs API capturadas no painel ===")
    for u in captured_urls:
        print(" ", u)

    # 3. Tentar API REST de etapas
    for eid in [TEST_EVENT_ID, "21688"]:
        for api_url in [
            "https://api.agendaoffroad.com.br/evento/%s/etapas" % eid,
            "https://api.agendaoffroad.com.br/eventoxetapa/%s" % eid,
        ]:
            try:
                resp = page.request.get(api_url, timeout=10000)
                print("\n=== GET %s ===" % api_url)
                print("Status:", resp.status)
                if resp.ok:
                    print(str(resp.json())[:500])
            except Exception as ex:
                print("  ERRO:", str(ex)[:80])

    # 4. Verificar o painel sem filtro — quais URLs são chamadas
    print("\n=== Painel principal sem filtro — URLs API ===")
    captured2 = []
    page.on("response", lambda r: captured2.append(r.url) if "api." in r.url or "eventoxetapa" in r.url else None)
    page.goto("https://agendaesportiva.com.br/admin/controller/painel/?ref=area-do-organizador")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(5000)
    for u in captured2:
        print(" ", u)

    browser.close()
