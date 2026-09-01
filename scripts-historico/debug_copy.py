"""Diagnóstico detalhado dos erros de duplicação."""
import sys, json, requests
sys.path.insert(0, __import__('os').path.expanduser('~/.adforge/daily_analyst'))
from common import load_env

env     = load_env()
token   = env.get('META_ACCESS_TOKEN', '')
api_ver = env.get('META_API_VERSION', 'v25.0')

# ── Teste 1: verificar o erro completo do RMKT ──────────────────────────────
print('=== Teste cópia RMKT (erro detalhado) ===')
resp = requests.post(
    'https://graph.facebook.com/%s/120249458187120761/copies' % api_ver,
    data={'deep_copy': '1', 'status_option': 'PAUSED',
          'name': '[RMKT] 3ª Etapa [COPIA]', 'access_token': token},
)
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

# ── Teste 2: verificar o campo da campanha Prospecto copiada ─────────────────
NEW_PROSP = '120249599606910761'
print('\n=== Campos da campanha copiada (Prospecto) ===')
r = requests.get(
    'https://graph.facebook.com/%s/%s' % (api_ver, NEW_PROSP),
    params={'fields': 'id,name,status,objective,daily_budget,lifetime_budget,budget_rebalance_flag,end_time',
            'access_token': token},
)
print(json.dumps(r.json(), indent=2, ensure_ascii=False))

# ── Teste 3: PATCH lifetime com end_time em unix timestamp ───────────────────
print('\n=== Tentativa PATCH lifetime (timestamp unix) ===')
import time
from datetime import datetime, timezone, timedelta
end_dt = datetime(2026, 8, 27, 23, 59, 0, tzinfo=timezone(timedelta(hours=-3)))
end_unix = int(end_dt.timestamp())
patch = requests.post(
    'https://graph.facebook.com/%s/%s' % (api_ver, NEW_PROSP),
    data={'lifetime_budget': '250000', 'end_time': str(end_unix), 'access_token': token},
)
print(json.dumps(patch.json(), indent=2, ensure_ascii=False))

# ── Teste 4: PATCH só end_time primeiro ──────────────────────────────────────
print('\n=== Tentativa PATCH só end_time ===')
p2 = requests.post(
    'https://graph.facebook.com/%s/%s' % (api_ver, NEW_PROSP),
    data={'end_time': str(end_unix), 'access_token': token},
)
print(json.dumps(p2.json(), indent=2, ensure_ascii=False))
