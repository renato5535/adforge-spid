"""Cria ou atualiza a pagina WordPress /tiktok-callback/ com redirect para localhost:8080"""
import os, json, base64, requests
from pathlib import Path

def load_env():
    env = {}
    for line in (Path.home() / '.adforge/.env').read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env

env = load_env()
WP_URL  = env['WP_URL']
WP_USER = env['WP_USER']
WP_PASS = env['WP_APP_PASSWORD']

auth = base64.b64encode(('%s:%s' % (WP_USER, WP_PASS)).encode()).decode()
headers = {
    'Authorization': 'Basic %s' % auth,
    'Content-Type': 'application/json',
}

page_content = (
    '<!-- wp:html -->\n'
    '<script>\n'
    '(function(){\n'
    '  var params = window.location.search;\n'
    '  if (params) {\n'
    "    window.location.replace('http://localhost:8080/callback' + params);\n"
    '  } else {\n'
    "    document.write('<p>TikTok callback — sem parametros recebidos.</p>');\n"
    '  }\n'
    '})();\n'
    '</script>\n'
    '<!-- /wp:html -->'
)

payload = {
    'title': 'TikTok OAuth Callback',
    'slug': 'tiktok-callback',
    'content': page_content,
    'status': 'publish',
    'comment_status': 'closed',
    'ping_status': 'closed',
}

# Verificar se a pagina ja existe
existing = requests.get('%s/wp-json/wp/v2/pages?slug=tiktok-callback' % WP_URL, headers=headers, timeout=15).json()
if existing:
    pid = existing[0]['id']
    r = requests.post('%s/wp-json/wp/v2/pages/%d' % (WP_URL, pid), headers=headers, json=payload, timeout=15)
    action = 'atualizada'
else:
    r = requests.post('%s/wp-json/wp/v2/pages' % WP_URL, headers=headers, json=payload, timeout=15)
    action = 'criada'

if r.ok:
    print('Pagina /tiktok-callback/ %s com sucesso' % action)
    print('URL:', WP_URL + '/tiktok-callback/')
else:
    print('Erro %d: %s' % (r.status_code, r.text[:300]))
