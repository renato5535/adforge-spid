"""Debug detalhado dos erros de cópia de adset e ads."""
import sys, json, requests
sys.path.insert(0, __import__('os').path.expanduser('~/.adforge/daily_analyst'))
from common import load_env

env     = load_env()
token   = env.get('META_ACCESS_TOKEN', '')
api_ver = env.get('META_API_VERSION', 'v25.0')
BASE    = 'https://graph.facebook.com/%s' % api_ver

NEW_PROSP_CAMP = '120249601369080761'
NEW_RMKT_CAMP  = '120249601416320761'
NEW_A01_ADSET  = '120249601389590761'  # já copiado com sucesso

def api_post_verbose(path, data):
    d = {'access_token': token}; d.update(data)
    r = requests.post('%s/%s' % (BASE, path), data=d)
    return r.json()

def api_get(path, params=None):
    p = {'access_token': token}
    if params: p.update(params)
    return requests.get('%s/%s' % (BASE, path), params=p).json()

# ── 1. Erro do adset A-02 (Engajamento 365D) ────────────────────────────────
print('=== Cópia adset A-02 para campanha Prospecto (verbose) ===')
r = api_post_verbose('120249458308050761/copies', {  # A-02 ID — vou buscar dinâmico
    'campaign_id': NEW_PROSP_CAMP,
    'status_option': 'PAUSED',
})
# buscar ID do A-02 primeiro
adsets = api_get('%s/adsets' % '120249458187670761', {
    'fields': 'id,name,effective_status',
    'filtering': json.dumps([{"field": "effective_status", "operator": "IN", "value": ["ACTIVE"]}]),
})
print('Adsets ativos Prospecto original:')
for a in adsets.get('data', []):
    print('  %s | %s | %s' % (a['id'], a['name'], a['effective_status']))

# copiar A-02 com erro detalhado
a02_id = None
for a in adsets.get('data', []):
    if 'Engajamento' in a['name']:
        a02_id = a['id']
if a02_id:
    print('\nCopiando A-02 (%s) para campanha Prospecto:' % a02_id)
    r2 = api_post_verbose('%s/copies' % a02_id, {
        'campaign_id': NEW_PROSP_CAMP,
        'status_option': 'PAUSED',
    })
    print(json.dumps(r2, indent=2, ensure_ascii=False))

# ── 2. Erro do adset B-01 ────────────────────────────────────────────────────
print('\n=== Cópia adset B-01 para campanha RMKT (verbose) ===')
b_adsets = api_get('%s/adsets' % '120249458187120761', {
    'fields': 'id,name,effective_status',
    'filtering': json.dumps([{"field": "effective_status", "operator": "IN", "value": ["ACTIVE"]}]),
})
for a in b_adsets.get('data', []):
    print('  %s | %s | %s' % (a['id'], a['name'], a['effective_status']))
    r3 = api_post_verbose('%s/copies' % a['id'], {
        'campaign_id': NEW_RMKT_CAMP,
        'status_option': 'PAUSED',
    })
    print(json.dumps(r3, indent=2, ensure_ascii=False))

# ── 3. Erro dos ads do A-01 ──────────────────────────────────────────────────
print('\n=== Ads do adset A-01 original (buscar IDs) ===')
a01_orig = None
for a in adsets.get('data', []):
    if 'LKL' in a['name'] or 'Purchase' in a['name']:
        a01_orig = a['id']
if a01_orig:
    ads = api_get('%s/ads' % a01_orig, {
        'fields': 'id,name,effective_status',
        'filtering': json.dumps([{"field": "effective_status", "operator": "IN",
                                  "value": ["ACTIVE", "PAUSED"]}]),
    })
    print('Ads em A-01 (%s):' % a01_orig)
    for ad in ads.get('data', []):
        print('  %s | %s | %s' % (ad['id'], ad['name'][:50], ad['effective_status']))

    # tentar copiar o segundo ad (o primeiro já foi copiado)
    ad_list = ads.get('data', [])
    if len(ad_list) > 1:
        ad = ad_list[1]
        print('\nTentando copiar ad[1] (%s):' % ad['id'])
        r4 = api_post_verbose('%s/copies' % ad['id'], {
            'adset_id': NEW_A01_ADSET,
            'status_option': 'PAUSED',
        })
        print(json.dumps(r4, indent=2, ensure_ascii=False))
