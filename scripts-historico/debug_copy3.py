"""Testa copiar adset com targeting override (advantage_audience=0 injetado)."""
import sys, json, requests
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

def api_get(path, params=None):
    p = {'access_token': token}
    if params: p.update(params)
    return requests.get('%s/%s' % (BASE, path), params=p).json()

def api_post_verbose(path, data):
    d = {'access_token': token}; d.update(data)
    r = requests.post('%s/%s' % (BASE, path), data=d)
    return r.json()

# Buscar targeting do A-02
a02 = api_get('120249458543460761', {'fields': 'targeting,optimization_goal,billing_event,bid_strategy,promoted_object,destination_type,attribution_spec'})
targeting = a02.get('targeting', {})
print('Targeting original A-02:')
print(json.dumps(targeting, indent=2, ensure_ascii=False))

# Injetar advantage_audience=0
targeting.setdefault('targeting_automation', {})['advantage_audience'] = 0

# Tentar 1: copies com deep_copy=0 + campaign_id + end_time
print('\n--- Tentativa 1: copies com campaign_id + end_time ---')
r1 = api_post_verbose('120249458543460761/copies', {
    'campaign_id': NEW_PROSP_CAMP,
    'deep_copy': '0',
    'status_option': 'PAUSED',
    'end_time': end_unix,
})
print(json.dumps(r1, indent=2, ensure_ascii=False))

# Tentar 2: copies sem deep_copy, com targeting override
print('\n--- Tentativa 2: copies com targeting override (targeting_automation) ---')
r2 = api_post_verbose('120249458543460761/copies', {
    'campaign_id': NEW_PROSP_CAMP,
    'status_option': 'PAUSED',
    'targeting': json.dumps(targeting),
    'end_time': end_unix,
})
print(json.dumps(r2, indent=2, ensure_ascii=False))

# Tentar 3: copies sem campaign_id (fica na campanha original)
print('\n--- Tentativa 3: copies simples (sem campaign override) ---')
r3 = api_post_verbose('120249458543460761/copies', {
    'status_option': 'PAUSED',
})
print(json.dumps(r3, indent=2, ensure_ascii=False))
