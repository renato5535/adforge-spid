"""
Pausa todos os ads de FAMÍLIA ativos.
Vendas do ingresso família encerraram em 28/08/2026 às 18h.

Ação:
- Lista ads ativos cujo nome contém 'familia' ou 'família' (case-insensitive)
- Pausa cada um via PATCH /ad/{id}?status=PAUSED
- Imprime resumo
"""
import sys, json
sys.path.insert(0, __import__('os').path.expanduser('~/.adforge/daily_analyst'))
from common import load_env, http_get_json, http_post_json

env     = load_env()
token   = env.get('META_ACCESS_TOKEN', '')
api_ver = env.get('META_API_VERSION', 'v25.0')
account = env.get('META_AD_ACCOUNT_ID', '')

BASE = 'https://graph.facebook.com/%s' % api_ver

# --- 1. Busca todos os ads ativos/em processo ---
url = '%s/%s/ads' % (BASE, account)
params = {
    'fields': 'id,name,status,effective_status,adset_id,adset{name,status}',
    'filtering': json.dumps([
        {"field": "effective_status", "operator": "IN",
         "value": ["ACTIVE", "IN_PROCESS", "WITH_ISSUES"]}
    ]),
    'limit': '200',
    'access_token': token,
}

data, err = http_get_json(url, params)
if err:
    print('ERRO ao listar ads:', err)
    sys.exit(1)

all_ads = data.get('data', [])

# --- 2. Filtra ads de família ---
keywords = ['familia', 'família', 'fam']
familia_ads = [
    ad for ad in all_ads
    if any(kw in ad.get('name', '').lower() for kw in keywords)
]

print('\n=== ADS DE FAMÍLIA ATIVOS ===')
if not familia_ads:
    print('Nenhum ad de família ativo encontrado.')
    sys.exit(0)

for ad in familia_ads:
    adset_name = (ad.get('adset') or {}).get('name', '?')
    print('  [%s] %s  (adset: %s)' % (
        ad.get('effective_status', '?'),
        ad.get('name', '?'),
        adset_name,
    ))

print('\n--- Pausando %d ad(s)... ---' % len(familia_ads))

paused_ok = []
paused_fail = []

for ad in familia_ads:
    ad_id = ad['id']
    ad_name = ad.get('name', ad_id)

    patch_url = '%s/%s' % (BASE, ad_id)
    payload = {
        'status': 'PAUSED',
        'access_token': token,
    }

    # Meta aceita POST com método emulado para PATCH — usamos POST com ?method=POST
    # mas a API de ads aceita POST diretamente para update de status
    resp, err = http_post_json(patch_url, payload)

    if err:
        print('  FALHA [%s]: %s — %s' % (ad_id, ad_name, err))
        paused_fail.append(ad_name)
    else:
        success = resp.get('success', False)
        if success:
            print('  OK  [%s]: %s' % (ad_id, ad_name))
            paused_ok.append(ad_name)
        else:
            print('  ERR [%s]: %s — %s' % (ad_id, ad_name, json.dumps(resp)))
            paused_fail.append(ad_name)

print('\n=== RESUMO ===')
print('Pausados com sucesso : %d' % len(paused_ok))
print('Falhas               : %d' % len(paused_fail))
if paused_fail:
    for n in paused_fail:
        print('  - %s' % n)
