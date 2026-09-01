"""
Cria os adsets A-02 e B-01 nas novas campanhas usando targeting completo do original
+ advantage_audience=0 explícito. Depois copia 1 ad de cada (são DCO).
"""
import sys, json, time, requests
sys.path.insert(0, __import__('os').path.expanduser('~/.adforge/daily_analyst'))
from common import load_env

env     = load_env()
token   = env.get('META_ACCESS_TOKEN', '')
api_ver = env.get('META_API_VERSION', 'v25.0')
account = env.get('META_AD_ACCOUNT_ID', 'act_881694943239418')
BASE    = 'https://graph.facebook.com/%s' % api_ver

from datetime import datetime, timezone, timedelta
end_dt   = datetime(2026, 8, 27, 23, 59, 0, tzinfo=timezone(timedelta(hours=-3)))
end_unix = str(int(end_dt.timestamp()))

NEW_PROSP_CAMP = '120249601369080761'
NEW_RMKT_CAMP  = '120249601416320761'

ADSETS_TO_COPY = [
    ('120249458543460761', 'A-02 Engajamento 365D',      NEW_PROSP_CAMP),
    ('120249458539200761', 'B-01 Video View 95% 180D',   NEW_RMKT_CAMP),
]

def api_get(path, params=None):
    p = {'access_token': token}
    if params: p.update(params)
    r = requests.get('%s/%s' % (BASE, path), params=p)
    return r.json()

def api_post(path, data):
    d = {'access_token': token}; d.update(data)
    return requests.post('%s/%s' % (BASE, path), data=d).json()

results = []

for as_id, as_name, camp_id in ADSETS_TO_COPY:
    print('\n=== %s ===' % as_name)

    # ── 1. Buscar detalhes completos do adset original ───────────────
    detail = api_get(as_id, {'fields': (
        'name,status,targeting,optimization_goal,billing_event,'
        'bid_strategy,promoted_object,destination_type,'
        'start_time,attribution_spec'
    )})
    if 'error' in detail:
        print('ERRO buscando adset: %s' % detail['error'].get('message'))
        continue

    targeting = detail.get('targeting', {})
    # setar advantage_audience=0 para manter targeting manual
    ta = targeting.get('targeting_automation', {})
    ta['advantage_audience'] = 0
    targeting['targeting_automation'] = ta

    # ── 2. Criar novo adset na nova campanha ─────────────────────────
    new_as_data = {
        'campaign_id': camp_id,
        'name': as_name + ' [COPIA]',
        'status': 'PAUSED',
        'targeting': json.dumps(targeting),
        'optimization_goal': detail.get('optimization_goal', 'OFFSITE_CONVERSIONS'),
        'billing_event': detail.get('billing_event', 'IMPRESSIONS'),
    }
    if detail.get('bid_strategy'):
        new_as_data['bid_strategy'] = detail['bid_strategy']
    if detail.get('promoted_object'):
        new_as_data['promoted_object'] = json.dumps(detail['promoted_object'])
    if detail.get('destination_type'):
        new_as_data['destination_type'] = detail['destination_type']
    if detail.get('attribution_spec'):
        new_as_data['attribution_spec'] = json.dumps(detail['attribution_spec'])
    # DCO desativado conforme política AdForge (feedback_meta_dynamic_creative)
    new_as_data['use_dynamic_creative'] = '0'
    if detail.get('start_time'):
        new_as_data['start_time'] = detail['start_time']
    new_as_data['end_time'] = end_unix

    print('  Criando adset na conta (campaign_id=%s)...' % camp_id)
    new_as = api_post('%s/adsets' % account, new_as_data)
    if 'error' in new_as:
        print('  ERRO criando adset: %s' % new_as['error'].get('message'))
        print('  Detalhe:', json.dumps(new_as['error'], ensure_ascii=False))
        continue

    new_as_id = new_as.get('id', '')
    print('  Adset criado → ID: %s' % new_as_id)
    time.sleep(0.5)

    # ── 3. Copiar 1 ad do adset original (DCO — só 1 é suficiente) ──
    ads = api_get('%s/ads' % as_id, {
        'fields': 'id,name,effective_status',
        'filtering': json.dumps([{"field": "effective_status", "operator": "IN",
                                  "value": ["ACTIVE"]}]),
        'limit': '1',
    })
    ad_list = ads.get('data', [])
    if not ad_list:
        print('  Nenhum ad ACTIVE encontrado no adset original')
        results.append({'adset': as_name, 'new_id': new_as_id, 'ads': 0})
        continue

    ad = ad_list[0]
    print('  Copiando ad: %s' % ad.get('name', '?')[:50])
    copy_ad = api_post('%s/copies' % ad['id'], {
        'adset_id': new_as_id,
        'status_option': 'PAUSED',
    })
    if 'error' in copy_ad:
        print('  ERRO copiando ad: %s' % copy_ad['error'].get('message'))
        results.append({'adset': as_name, 'new_id': new_as_id, 'ads': 0})
    else:
        new_ad_id = copy_ad.get('copied_ad_id') or copy_ad.get('id', '')
        print('  Ad copiado → ID: %s' % new_ad_id)
        results.append({'adset': as_name, 'new_id': new_as_id, 'ads': 1, 'ad_id': new_ad_id})

print('\n' + '=' * 60)
print('RESUMO:')
for r in results:
    print('  %-35s → adset %s | %d ad(s)' % (r['adset'], r.get('new_id', '?'), r.get('ads', 0)))

# Atualizar o JSON de resultados
out = __import__('os').path.expanduser('~/.adforge/etapa3_copy_ids.json')
try:
    with open(out, encoding='utf-8') as f:
        data = json.load(f)
except Exception:
    data = {}
data['advantage_adsets'] = results
with open(out, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('\nResultados atualizados em %s' % out)
