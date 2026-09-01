"""Diagnóstico de delivery por dia das duas campanhas da 3ª Etapa."""
import sys, json
sys.path.insert(0, __import__('os').path.expanduser('~/.adforge/daily_analyst'))
from common import load_env, http_get_json

env     = load_env()
token   = env.get('META_ACCESS_TOKEN', '')
api_ver = env.get('META_API_VERSION', 'v25.0')

CAMP_IDS = {
    '120249458187670761': '[PROSPECTO] 3ª Etapa',
    '120249458187120761': '[RMKT] 3ª Etapa',
}

for cid, label in CAMP_IDS.items():
    print('\n=== %s (ID: %s) ===' % (label, cid))
    url = 'https://graph.facebook.com/%s/%s/insights' % (api_ver, cid)
    params = {
        'fields': 'date_start,date_stop,impressions,reach,spend,clicks',
        'time_increment': '1',
        'date_preset': 'last_14d',
        'access_token': token,
    }
    data, err = http_get_json(url, params)
    if err:
        print('ERRO:', err)
        continue
    rows = data.get('data', [])
    if not rows:
        print('Sem dados de insights')
        continue
    print('%-12s %-12s %-10s %-10s %-10s' % ('Data', 'Impressões', 'Alcance', 'Cliques', 'Gasto'))
    print('-' * 60)
    for r in rows:
        impr = r.get('impressions', '0')
        reach = r.get('reach', '0')
        clicks = r.get('clicks', '0')
        spend = r.get('spend', '0')
        ds   = r.get('date_start', '')
        flag = ' ⚠️ ZERO' if impr == '0' else ''
        print('%-12s %-12s %-10s %-10s R$%-8s%s' % (ds, impr, reach, clicks, spend, flag))

# Também checar adsets ativos
print('\n\n=== Adsets da 3ª Etapa ===')
for cid, label in CAMP_IDS.items():
    url2 = 'https://graph.facebook.com/%s/%s/adsets' % (api_ver, cid)
    p2 = {
        'fields': 'id,name,status,effective_status,daily_budget,lifetime_budget,insights{impressions,spend}',
        'date_preset': 'last_7d',
        'access_token': token,
    }
    d2, e2 = http_get_json(url2, p2)
    if e2:
        print('ERRO adsets %s: %s' % (cid, e2))
        continue
    print('\n%s:' % label)
    for a in d2.get('data', []):
        nm  = a.get('name', '?')
        st  = a.get('effective_status', '?')
        db  = int(a.get('daily_budget', 0)) // 100
        lb  = int(a.get('lifetime_budget', 0)) // 100
        bgt = ('R$%d/dia' % db) if db else ('R$%d total' % lb) if lb else 'sem'
        ins = ((a.get('insights') or {}).get('data') or [{}])[0]
        impr = ins.get('impressions', '0')
        spend = ins.get('spend', '0')
        print('  [%-14s] %-50s %s | impr=%s spend=R$%s' % (st, nm, bgt, impr, spend))
