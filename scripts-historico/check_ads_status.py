"""Lista adsets + ads com status e data de criação."""
import sys, json
sys.path.insert(0, __import__('os').path.expanduser('~/.adforge/daily_analyst'))
from common import load_env, http_get_json

env     = load_env()
token   = env.get('META_ACCESS_TOKEN', '')
api_ver = env.get('META_API_VERSION', 'v25.0')
account = env.get('META_AD_ACCOUNT_ID', 'act_881694943239418')

url = 'https://graph.facebook.com/%s/%s/adsets' % (api_ver, account)
params = {
    'fields': 'id,name,status,campaign_id,daily_budget,campaign{name},ads{id,name,status,created_time,effective_status}',
    'filtering': json.dumps([{"field": "effective_status", "operator": "IN",
                              "value": ["ACTIVE", "PAUSED", "IN_PROCESS", "WITH_ISSUES"]}]),
    'limit': '100',
    'access_token': token,
}
data, err = http_get_json(url, params)
if err:
    print('ERRO:', err)
    sys.exit(1)

adsets = sorted(data.get('data', []), key=lambda x: x.get('name', ''))
print('\n%-3s %-55s %8s %6s' % ('ST', 'Adset', 'Budget', 'Ads'))
print('-' * 80)
for adset in adsets:
    nm     = adset.get('name', '?')[:55]
    st     = adset.get('status', '?')[:3]
    budget = int(adset.get('daily_budget', 0)) // 100
    camp   = (adset.get('campaign') or {}).get('name', '')[:30]
    ads    = adset.get('ads', {}).get('data', [])
    print('[%s] %-55s R$%4d/dia | %d ads | %s' % (st, nm, budget, len(ads), camp))
    for ad in sorted(ads, key=lambda x: x.get('created_time', ''), reverse=True):
        anm = ad.get('name', '?')[:65]
        ast = ad.get('effective_status', '?')
        ct  = ad.get('created_time', '')[:16].replace('T', ' ')
        print('    [%-14s] %-65s %s' % (ast, anm, ct))
