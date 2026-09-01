"""Fase 1 — Pausar adsets com audiences vazias + budget bounce."""
import json, urllib.request, urllib.parse, time, os

env = {}
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"')

TOKEN = env.get('META_ACCESS_TOKEN', '')
ACCOUNT = env.get('META_AD_ACCOUNT_ID', 'act_881694943239418')
VER = 'v25.0'
GRAPH = 'https://graph.facebook.com'


def get(node, params, t=10):
    p = dict(params)
    p['access_token'] = TOKEN
    url = '%s/%s/%s?%s' % (GRAPH, VER, node, urllib.parse.urlencode(p))
    try:
        with urllib.request.urlopen(url, timeout=t) as r:
            return json.loads(r.read()), None
    except Exception as e:
        return None, str(e)[:120]


def post_update(node, field, value, t=10):
    url = '%s/%s/%s' % (GRAPH, VER, node)
    body = urllib.parse.urlencode({'access_token': TOKEN, field: value}).encode()
    try:
        req = urllib.request.Request(url, data=body, method='POST')
        with urllib.request.urlopen(req, timeout=t) as r:
            return json.loads(r.read()), None
    except Exception as e:
        return None, str(e)[:120]


# ── 1. Pausar adsets com audiences de pixel (sz=20) ───────────────
print('=== FASE 1A: Pausar adsets com audiences vazias ===')
ADSETS_PAUSAR = [
    ('120249458523540761', 'B-00 Pageview 180D'),
    ('120249458540310761', 'B-02 Purchase 180D'),
    ('120249458541220761', 'B-03 InitiateCheckout 180D'),
]
for adset_id, nome in ADSETS_PAUSAR:
    r, e = post_update(adset_id, 'status', 'PAUSED')
    ok = r and r.get('success')
    print('  %s: %s' % (nome, 'PAUSADO' if ok else ('ERRO: %s' % (e or str(r)))))
    time.sleep(1.5)

# ── 2. Budget bounce em campanhas ativas ───────────────────────────
print()
print('=== FASE 1B: Budget bounce para forçar re-alocação ===')

# Pegar campanhas individualmente pelos IDs conhecidos
# Prospecto e RMKT — IDs mapeados a partir dos adsets (campaign_id nos adsets)
# A-02: campaign provavelmente é a Prospecto
# Listar campanhas ativas
r_c, e_c = get('%s/campaigns' % ACCOUNT, {
    'fields': 'id,name,daily_budget,effective_status,budget_remaining',
    'limit': '30',
})
if e_c:
    print('  ERRO listar campanhas: %s' % e_c)
else:
    ativas = [c for c in (r_c or {}).get('data', []) if c.get('effective_status') == 'ACTIVE']
    print('  Campanhas ACTIVE: %d' % len(ativas))
    for c in ativas:
        bud = c.get('daily_budget')
        if not bud:
            print('  %-40s: sem daily_budget (pular)' % c.get('name', '?')[:40])
            continue
        bud_i = int(bud)
        # +R$1
        r1, e1 = post_update(c['id'], 'daily_budget', str(bud_i + 100))
        time.sleep(1)
        # Volta
        r2, e2 = post_update(c['id'], 'daily_budget', str(bud_i))
        ok = (r1 and r1.get('success')) and (r2 and r2.get('success'))
        print('  %-40s: budget bounce %s centavos | %s%s' % (
            c.get('name', '?')[:40], bud_i,
            'OK' if ok else 'FALHOU',
            (' | %s' % (e1 or e2)) if (e1 or e2) else ''
        ))
        time.sleep(1.5)

print()
print('FASE 1 CONCLUIDA')
