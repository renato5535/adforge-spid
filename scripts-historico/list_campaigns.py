"""Lista campanhas ativas e pausadas com status e orçamento."""
import sys, json
sys.path.insert(0, __import__('os').path.expanduser('~/.adforge/daily_analyst'))
from common import load_env, http_get_json

env     = load_env()
token   = env.get('META_ACCESS_TOKEN', '')
api_ver = env.get('META_API_VERSION', 'v25.0')
account = env.get('META_AD_ACCOUNT_ID', 'act_881694943239418')

url = 'https://graph.facebook.com/%s/%s/campaigns' % (api_ver, account)
params = {
    'fields': 'id,name,status,effective_status,objective,daily_budget,lifetime_budget,budget_remaining,created_time,start_time,stop_time,insights{impressions,reach,spend}',
    'filtering': json.dumps([{"field": "effective_status", "operator": "IN",
                              "value": ["ACTIVE", "PAUSED", "IN_PROCESS", "WITH_ISSUES"]}]),
    'date_preset': 'last_7d',
    'limit': '50',
    'access_token': token,
}
data, err = http_get_json(url, params)
if err:
    print('ERRO:', err)
    sys.exit(1)

campaigns = sorted(data.get('data', []), key=lambda x: x.get('created_time', ''), reverse=True)
print('\n%s campanhas encontradas\n' % len(campaigns))
print('%-20s %-60s %-8s %-12s %-8s' % ('ID', 'Nome', 'Status', 'Budget', 'Impressões'))
print('-' * 120)
for c in campaigns:
    cid     = c.get('id', '?')
    nm      = c.get('name', '?')[:60]
    st      = c.get('effective_status', '?')
    db      = int(c.get('daily_budget', 0)) // 100
    lb      = int(c.get('lifetime_budget', 0)) // 100
    budget  = ('R$%d/dia' % db) if db else (('R$%d total' % lb) if lb else 'sem budget')
    ins_raw = (c.get('insights') or {}).get('data', [{}])
    ins     = ins_raw[0] if ins_raw else {}
    impr    = ins.get('impressions', '0')
    spend   = ins.get('spend', '0')
    ct      = c.get('created_time', '')[:10]
    print('[%-14s] %-20s %-60s %-14s impressões=%s spend=R$%s (criado %s)' % (st, cid, nm, budget, impr, spend, ct))
