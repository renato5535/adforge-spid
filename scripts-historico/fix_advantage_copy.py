"""
Estratégia: PATCH adset original com targeting_automation.advantage_audience=0,
copiar, depois reverter o original ao estado anterior.
"""
import sys, json, time, requests
sys.path.insert(0, __import__('os').path.expanduser('~/.adforge/daily_analyst'))
from common import load_env

env     = load_env()
token   = env.get('META_ACCESS_TOKEN', '')
api_ver = env.get('META_API_VERSION', 'v25.0')
BASE    = 'https://graph.facebook.com/%s' % api_ver

NEW_PROSP_CAMP = '120249601369080761'
NEW_RMKT_CAMP  = '120249601416320761'

from datetime import datetime, timezone, timedelta
end_dt   = datetime(2026, 8, 27, 23, 59, 0, tzinfo=timezone(timedelta(hours=-3)))
end_unix = str(int(end_dt.timestamp()))

ADSETS = [
    ('120249458543460761', 'A-02 Engajamento 365D',    NEW_PROSP_CAMP),
    ('120249458539200761', 'B-01 Video View 95% 180D', NEW_RMKT_CAMP),
]

def api_get(path, params=None):
    p = {'access_token': token}
    if params: p.update(params)
    return requests.get('%s/%s' % (BASE, path), params=p).json()

def api_post(path, data):
    d = {'access_token': token}; d.update(data)
    return requests.post('%s/%s' % (BASE, path), data=d).json()

results = []

for as_id, as_name, camp_id in ADSETS:
    print('\n=== %s (%s) ===' % (as_name, as_id))

    # Buscar targeting original
    orig = api_get(as_id, {'fields': 'targeting'})
    orig_targeting = orig.get('targeting', {})

    # Fazer cópia do targeting sem modificar, só para reverter depois
    revert_targeting = json.loads(json.dumps(orig_targeting))

    # Modificar targeting com advantage_audience=0
    patch_targeting = json.loads(json.dumps(orig_targeting))
    patch_targeting.setdefault('targeting_automation', {})['advantage_audience'] = 0

    print('  PATCH no original adicionando advantage_audience=0...')
    patch_resp = api_post(as_id, {'targeting': json.dumps(patch_targeting)})
    if 'error' in patch_resp:
        print('  ERRO no PATCH: %s' % patch_resp['error'].get('message'))
        continue
    print('  PATCH OK: %s' % patch_resp)
    time.sleep(1)

    # Copiar adset agora
    print('  Copiando adset para nova campanha...')
    copy_resp = api_post('%s/copies' % as_id, {
        'campaign_id': camp_id,
        'status_option': 'PAUSED',
        'end_time': end_unix,
    })
    new_as_id = None
    if 'error' in copy_resp:
        print('  ERRO na cópia: %s' % copy_resp['error'].get('message'))
    else:
        new_as_id = copy_resp.get('copied_adset_id') or copy_resp.get('id', '')
        print('  Adset copiado → ID: %s' % new_as_id)

    # Reverter targeting original
    print('  Revertendo targeting original...')
    if revert_targeting.get('targeting_automation') is None:
        # Se não tinha targeting_automation, setar advantage_audience=0 mas de forma mínima
        # Na verdade, reverter sem targeting_automation (remover o campo)
        revert_targeting.pop('targeting_automation', None)
    rev_resp = api_post(as_id, {'targeting': json.dumps(revert_targeting)})
    if 'error' in rev_resp:
        print('  AVISO: erro ao reverter targeting: %s' % rev_resp['error'].get('message'))
    else:
        print('  Revertido OK')

    if not new_as_id:
        results.append({'adset': as_name, 'status': 'ERRO'})
        continue

    # Copiar 1 ad ACTIVE do adset original para o novo
    print('  Buscando ads ativos no original...')
    ads = api_get('%s/ads' % as_id, {
        'fields': 'id,name,effective_status',
        'filtering': json.dumps([{"field": "effective_status", "operator": "IN", "value": ["ACTIVE"]}]),
        'limit': '1',
    })
    ad_list = ads.get('data', [])
    if not ad_list:
        print('  Nenhum ad ACTIVE encontrado')
        results.append({'adset': as_name, 'new_id': new_as_id, 'status': 'SEM_AD'})
        continue

    ad = ad_list[0]
    print('  Copiando ad: %s' % ad.get('name', '?')[:50])
    copy_ad = api_post('%s/copies' % ad['id'], {
        'adset_id': new_as_id,
        'status_option': 'PAUSED',
    })
    if 'error' in copy_ad:
        print('  ERRO copiando ad: %s' % copy_ad['error'].get('message'))
        results.append({'adset': as_name, 'new_id': new_as_id, 'status': 'ERRO_AD'})
    else:
        new_ad_id = copy_ad.get('copied_ad_id') or copy_ad.get('id', '')
        print('  Ad copiado → %s' % new_ad_id)
        results.append({'adset': as_name, 'new_id': new_as_id, 'ad_id': new_ad_id, 'status': 'OK'})
    time.sleep(0.5)

print('\n' + '=' * 60)
print('RESUMO:')
for r in results:
    print('  [%-7s] %-35s adset=%s' % (r['status'], r['adset'], r.get('new_id', '-')))

# Atualizar JSON de resultado
out = __import__('os').path.expanduser('~/.adforge/etapa3_copy_ids.json')
try:
    with open(out, encoding='utf-8') as f:
        data = json.load(f)
except Exception:
    data = {}
data['advantage_adsets_v2'] = results
with open(out, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('JSON atualizado em %s' % out)
