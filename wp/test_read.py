# -*- coding: utf-8 -*-
"""Teste de leitura WordPress — execute APÓS configurar credenciais no .env.

NÃO EXECUTA NADA antes das credenciais estarem configuradas.

Pré-requisitos:
  1. Adicionar ao ~/.adforge/.env:
       WP_URL=https://seusite.com.br
       WP_USER=renato
       WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx

  2. Wordfence → All Options → Brute Force Protection
       □ Desmarcar "Disable WordPress Application Passwords"

  3. Executar (PowerShell):
       ~/.adforge/venv_wp/Scripts/python test_read.py

O teste faz SOMENTE leitura. Nenhuma página é modificada.
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wp_client import WPClient, WPAuthError, WPNotFoundError


def load_env():
    env = {}
    path = os.path.expanduser("~/.adforge/.env")
    if not os.path.exists(path):
        return env
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                v = v.strip().strip("'\"")
                env[k.strip()] = v
    return env


def _sep(title):
    print("\n%s\n=== %s ===" % ("─" * 50, title))


def main():
    env  = load_env()
    url  = env.get("WP_URL", "")
    user = env.get("WP_USER", "")
    pwd  = env.get("WP_APP_PASSWORD", "")

    if not all([url, user, pwd]):
        print("ERRO: Configure WP_URL, WP_USER e WP_APP_PASSWORD em ~/.adforge/.env")
        sys.exit(1)

    print("Conectando a %s como '%s'..." % (url, user))
    wp = WPClient(url, user, pwd)

    # ── Teste 1: listar páginas ───────────────────────────────────────────────
    _sep("Teste 1 — Listar páginas")
    try:
        pages = wp.list_pages(per_page=15)
    except WPAuthError as e:
        print("ERRO de autenticação: %s" % e)
        print("\nVerifique:")
        print("  1. Wordfence → All Options → Brute Force → desmarque 'Disable Application Passwords'")
        print("  2. Application Password gerado em Usuários → [seu usuário] → Application Passwords")
        print("  3. Firewall em Learning Mode temporariamente se ainda bloqueado")
        sys.exit(1)

    if not pages:
        print("Nenhuma página encontrada (verifique status='any' e permissões do usuário).")
        return

    for p in pages:
        print("  [%4d] %-40s status: %s" % (
            p["id"],
            p.get("title", {}).get("rendered", "?")[:40],
            p.get("status", "?"),
        ))

    # ── Teste 2: meta de uma página ───────────────────────────────────────────
    first_id = pages[0]["id"]
    _sep("Teste 2 — Meta da página [%d]" % first_id)
    try:
        page = wp.get_page_meta(first_id)
    except Exception as e:
        print("ERRO: %s" % e)
        return

    meta = page.get("meta") or {}
    print("  Meta fields expostos: %s" % list(meta.keys()))

    if "_elementor_data" not in meta:
        print("\n  ⚠️  _elementor_data não está exposto na REST API.")
        print("  Adicione ao functions.php do tema (ou plugin custom):")
        print()
        print("    register_post_meta('page', '_elementor_data', [")
        print("        'show_in_rest' => true,")
        print("        'single'       => true,")
        print("        'type'         => 'string',")
        print("    ]);")
        return

    # ── Teste 3: parse do Elementor data ─────────────────────────────────────
    _sep("Teste 3 — Parse _elementor_data")
    elements = wp.parse_elementor_data(page)
    if elements is None:
        print("  _elementor_data vazio ou nulo (página pode não usar Elementor).")
        return

    all_widgets = wp.find_widgets(elements)
    print("  Total de elementos (widgets): %d" % len(all_widgets))

    rows = wp.summarize_widgets(elements)
    print()
    print("  %-10s %-22s %-14s %s" % ("ID", "Tipo", "Status", "Preview"))
    print("  " + "-" * 80)
    for r in rows:
        print("  %-10s %-22s %-14s %s" % (
            r["id"], r["type"], r["status"], r["preview"][:40]
        ))

    # ── Teste 4: busca por tipo específico ───────────────────────────────────
    _sep("Teste 4 — Widgets 'heading' editáveis")
    headings = wp.find_widgets(elements, "heading")
    if not headings:
        print("  Nenhum widget 'heading' encontrado nesta página.")
    for h in headings:
        print("  id=%-10s título='%s'" % (
            h.get("id", "?"),
            h.get("settings", {}).get("title", "")[:60],
        ))

    print("\n" + "─" * 50)
    print("✅ Todos os testes de leitura passaram. Nenhuma modificação foi feita.")
    print("   Próximo passo: approve via Telegram → update_widget_setting + push_elementor_data")


if __name__ == "__main__":
    main()
