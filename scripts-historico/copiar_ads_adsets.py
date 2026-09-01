"""Copia 1 ad de cada adset original (qualquer status) para os adsets novos."""
import sys, json, time, requests
sys.path.insert(0, __import__('os').path.expanduser('~/.adforge/daily_analyst'))
from common import load_env

env   = load_env()
token = env.get('META_ACCESS_TOKEN', '')
BASE  = 'https://graph.facebook.com/%s' % env.get('META_API_VERSION', 'v25.0')

# orig_adset → novo_adset
PAIRS = [
    # A-02 Engajamento 365D (Prospecto)
    ('120249458543460761', '120249601937260761', 'A-02 Engajamento 365D'),
    # B-01 Video View 95% (RMKT)
    ('120249458539200761', '120249601941100761', 'B-01 Video View 95% 180D'),
    # A-01 LKL 1% Purchase (Prospecto) — já copiado 1 ad, copia os restantes
    ('120249458542640761', '120249601389590761', 'A-01 LKL 1% Purchase 180D'),
]

def api_get(path, params=None):
    p = {'access_token': token}
    if params: p.update(params)
    return requests.get('%s/%s' % (BASE, path), params=p).json()

def api_post(path, data):
    d = {'access_token': token}; d.update(data)
    return requests.post('%s/%s' % (BASE, path), data=d).json()

for orig_id, new_id, name in PAIRS:
    print('\n=== %s ===' % name)
    # Buscar todos os ads (qualquer status exceto DELETED/ARCHIVED)
    ads = api_get('%s/ads' % orig_id, {
        'fields': 'id,name,effective_status',
        'filtering': json.dumps([{"field": "effective_status", "operator": "IN",
                                  "value": ["ACTIVE", "PAUSED", "WITH_ISSUES",
                                            "ADSET_PAUSED", "CAMPAIGN_PAUSED"]}]),
        'limit': '1',
    })
    ad_list = ads.get('data', [])
    print('  Ads encontrados: %d' % len(ad_list))
    if not ad_list:
        print('  VAZIO — nenhum ad disponível')
        continue

    ad = ad_list[0]
    print('  Copiando: [%s] %s' % (ad.get('effective_status', '?'), ad.get('name', '?')[:55]))
    r = api_post('%s/copies' % ad['id'], {
        'adset_id': new_id,
        'status_option': 'PAUSED',
    })
    if 'error' in r:
        print('  ERRO: %s' % r['error'].get('message'))
    else:
        new_ad = r.get('copied_ad_id') or r.get('id', '?')
        print('  OK → novo ad: %s' % new_ad)
    time.sleep(0.4)
