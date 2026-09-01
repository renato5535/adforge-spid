"""
Cria duas campanhas novas com lifetime budget e copia adsets+ads individualmente.
Campanha original não é pausada aqui — script separado faz isso após publicação.
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

# Campanhas originais → lifetime budget desejado
ORIG = [
    ('120249458187670761', '[PROSPECTO][CONVERSÃO] 3ª Etapa SPID Cup 2026 [COPIA]', 250000, 'OUTCOME_SALES'),
    ('120249458187120761', '[RMKT][CONVERSÃO] 3ª Etapa SPID Cup 2026 [COPIA]',       280000, 'OUTCOME_SALES'),
]

def api_get(path, params=None):
    p = {'access_token': token}
    if params: p.update(params)
    r = requests.get('%s/%s' % (BASE, path), params=p)
    return r.json()

def api_post(path, data):
    d = {'access_token': token}
    d.update(data)
    r = requests.post('%s/%s' % (BASE, path), data=d)
    return r.json()

def ok(r):
    return 'error' not in r

results = {'campaigns': []}

for orig_id, new_name, lifetime_cents, objective in ORIG:
    print('\n' + '=' * 65)
    print('Processando: %s' % new_name)

    # ── 1. Buscar detalhes da campanha original ──────────────────────
    orig = api_get(orig_id, {'fields': 'id,name,objective,special_ad_categories,bid_strategy,budget_rebalance_flag'})
    if not ok(orig):
        print('  ERRO lendo campanha original: %s' % orig.get('error', {}).get('message'))
        continue

    # ── 2. Criar nova campanha com lifetime budget ───────────────────
    print('  Criando campanha com lifetime budget R$%d...' % (lifetime_cents // 100))
    camp_data = {
        'name': new_name,
        'objective': objective,
        'status': 'PAUSED',
        'special_ad_categories': '[]',
        'lifetime_budget': str(lifetime_cents),
        'end_time': end_unix,
    }
    bid = orig.get('bid_strategy')
    if bid:
        camp_data['bid_strategy'] = bid

    new_camp = api_post('%s/campaigns' % account, camp_data)
    if not ok(new_camp):
        print('  ERRO criando campanha: %s' % new_camp.get('error', {}).get('message'))
        continue
    new_camp_id = new_camp.get('id', '')
    print('  Campanha criada → ID: %s' % new_camp_id)

    # ── 3. Buscar adsets da campanha original (só ativos/com histórico) ──
    adsets_resp = api_get('%s/adsets' % orig_id, {
        'fields': 'id,name,status,effective_status',
        'filtering': json.dumps([{"field": "effective_status", "operator": "IN",
                                  "value": ["ACTIVE"]}]),
        'limit': '50',
    })
    adsets = adsets_resp.get('data', [])
    print('  Adsets ativos encontrados: %d' % len(adsets))

    camp_result = {'orig_id': orig_id, 'new_id': new_camp_id, 'name': new_name, 'adsets': []}

    for adset in adsets:
        as_id   = adset['id']
        as_name = adset.get('name', '?')
        print('\n  Copiando adset: %s' % as_name)

        # cópia shallow do adset para nova campanha (sem ads)
        copy_as = api_post('%s/copies' % as_id, {
            'campaign_id': new_camp_id,
            'deep_copy': '0',
            'status_option': 'PAUSED',
        })
        if not ok(copy_as):
            msg = copy_as.get('error', {}).get('message', str(copy_as))
            print('    ERRO copiando adset: %s — tentando método alternativo' % msg)
            # Fallback: criar cópia com deep_copy mas limite = 1 ad
            copy_as = api_post('%s/copies' % as_id, {
                'campaign_id': new_camp_id,
                'status_option': 'PAUSED',
            })
            if not ok(copy_as):
                print('    ERRO FATAL adset: %s' % copy_as.get('error', {}).get('message'))
                continue

        new_as_id = copy_as.get('copied_adset_id') or copy_as.get('id', '')
        print('    Adset copiado → ID: %s' % new_as_id)
        time.sleep(0.5)

        # ── 4. Buscar ads do adset original e copiar 1 a 1 ─────────
        ads_resp = api_get('%s/ads' % as_id, {
            'fields': 'id,name,effective_status',
            'filtering': json.dumps([{"field": "effective_status", "operator": "IN",
                                      "value": ["ACTIVE", "PAUSED"]}]),
            'limit': '50',
        })
        ads = ads_resp.get('data', [])
        print('    Ads no adset original: %d' % len(ads))

        ads_copied = []
        for ad in ads:
            ad_id   = ad['id']
            ad_name = ad.get('name', '?')
            copy_ad = api_post('%s/copies' % ad_id, {
                'adset_id': new_as_id,
                'status_option': 'PAUSED',
            })
            if not ok(copy_ad):
                msg = copy_ad.get('error', {}).get('message', '?')
                print('    Ad %s ERRO: %s' % (ad_name[:40], msg))
            else:
                new_ad_id = copy_ad.get('copied_ad_id') or copy_ad.get('id', '')
                print('    Ad %-40s → %s OK' % (ad_name[:40], new_ad_id))
                ads_copied.append({'orig': ad_id, 'new': new_ad_id, 'name': ad_name})
            time.sleep(0.3)

        camp_result['adsets'].append({
            'orig_id': as_id, 'new_id': new_as_id,
            'name': as_name, 'ads_copied': ads_copied,
        })

    results['campaigns'].append(camp_result)

# ── Salvar resultado ─────────────────────────────────────────────────────────
out = __import__('os').path.expanduser('~/.adforge/etapa3_copy_ids.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print('\n' + '=' * 65)
print('RESUMO FINAL:')
for c in results['campaigns']:
    total_ads = sum(len(a['ads_copied']) for a in c.get('adsets', []))
    print('  ✓ %s' % c['name'])
    print('    ID: %s | %d adsets | %d ads copiados' % (
        c['new_id'], len(c.get('adsets', [])), total_ads))
print('\nResultados salvos em %s' % out)
print('\n⚠️  Campanhas criadas PAUSADAS — revise no Gerenciador e publique.')
print('   Após publicar as novas, rode: python pausar_originais_etapa3.py')
