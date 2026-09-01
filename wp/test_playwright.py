"""
Teste WordPress via Playwright — bypassa Cloudflare com browser real.
Executa fetch() autenticado de dentro do contexto do browser.
"""
import asyncio
import os
import sys
from pathlib import Path

# Carrega .env
env_path = Path.home() / ".adforge" / ".env"
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        v = v.strip("'\"")
        os.environ.setdefault(k.strip(), v.strip())

WP_URL  = os.environ["WP_URL"]
WP_USER = os.environ["WP_USER"]
WP_PASS = os.environ["WP_APP_PASSWORD"]

async def main():
    from playwright.async_api import async_playwright
    import base64

    creds_b64 = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()

    print(f"Conectando a {WP_URL} via Playwright...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="pt-BR",
        )
        # Remove webdriver flag
        await ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await ctx.new_page()

        # Passa pelo Cloudflare carregando a página normalmente
        print("Resolvendo Cloudflare challenge...")
        await page.goto(WP_URL, wait_until="domcontentloaded", timeout=30000)

        # Aguarda até o título não ser mais "Just a moment..." (até 20s)
        for _ in range(20):
            title = await page.title()
            if "moment" not in title.lower():
                break
            await page.wait_for_timeout(1000)

        title = await page.title()
        print(f"Página carregada: {title}")

        # Faz REST API call de dentro do browser (cookie CF já válido)
        result = await page.evaluate(f"""async () => {{
            const resp = await fetch('/wp-json/wp/v2/pages?per_page=5&status=any', {{
                headers: {{
                    'Authorization': 'Basic {creds_b64}',
                    'Content-Type': 'application/json'
                }}
            }});
            const total = resp.headers.get('X-WP-Total');
            if (!resp.ok) {{
                return {{ ok: false, status: resp.status, body: (await resp.text()).slice(0, 200) }};
            }}
            const pages = await resp.json();
            return {{
                ok: true,
                status: resp.status,
                total: parseInt(total),
                firstTitle: pages[0]?.title?.rendered,
                titles: pages.map(p => p.title?.rendered)
            }};
        }}""")

        await browser.close()
        return result

result = asyncio.run(main())

print("\n" + "─" * 50)
if result.get("ok"):
    print(f"✅ Autenticação: OK (HTTP {result['status']})")
    print(f"📄 Total de páginas: {result['total']}")
    print(f"📌 Primeira página: {result['firstTitle']}")
    print(f"📋 Títulos encontrados:")
    for t in result.get("titles", []):
        print(f"   • {t}")
else:
    print(f"❌ Erro HTTP {result['status']}: {result['body']}")
