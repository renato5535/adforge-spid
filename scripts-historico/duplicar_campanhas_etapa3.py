"""Duplica as duas campanhas da 3ª Etapa (deep_copy PAUSED) e muda para lifetime budget."""
import sys, json, requests
sys.path.insert(0, __import__('os').path.expanduser('~/.adforge/daily_analyst'))
from common import load_env

env     = load_env()
token   = env.get('META_ACCESS_TOKEN', '')
api_ver = env.get('META_API_VERSION', 'v25.0')

# lifetime budget em centavos | end_time = véspera do evento
CAMPAIGNS = [
    ('120249458187670761', '[PROSPECTO][CONVERSÃO] 3ª Etapa SPID Cup 2026', 250000),  # R$2.500
    ('120249458187120761', '[RMKT][CONVERSÃO] 3ª Etapa SPID Cup 2026',       280000),  # R$2.800
]
END_TIME = '2026-08-27T23:59:00-0300'

results = []
for cid, name, lifetime_cents in CAMPAIGNS:
    print('=' * 60)
    print('Duplicando: %s' % name)

    # Passo 1 — deep_copy pausada
    url_copy = 'https://graph.facebook.com/%s/%s/copies' % (api_ver, cid)
    resp = requests.post(url_copy, data={
        'deep_copy': '1',
        'status_option': 'PAUSED',
        'name': name + ' [COPIA]',
        'access_token': token,
    })
    r = resp.json()
    if 'error' in r:
        msg = r['error'].get('message', str(r['error']))
        print('  ERRO na cópia: %s' % msg)
        results.append({'original_id': cid, 'status': 'ERRO_COPY', 'detalhe': msg})
        continue

    new_id = r.get('copied_campaign_id') or r.get('id', '')
    print('  Cópia criada → ID: %s' % new_id)

    # Passo 2 — setar lifetime_budget + end_time (remove daily_budget implicitamente)
    url_patch = 'https://graph.facebook.com/%s/%s' % (api_ver, new_id)
    patch_resp = requests.post(url_patch, data={
        'lifetime_budget': str(lifetime_cents),
        'end_time': END_TIME,
        'access_token': token,
    })
    pr = patch_resp.json()
    if 'error' in pr:
        msg = pr['error'].get('message', str(pr['error']))
        print('  AVISO: erro ao setar lifetime budget: %s' % msg)
        results.append({'original_id': cid, 'new_id': new_id, 'status': 'ERRO_BUDGET', 'detalhe': msg})
    else:
        budget_brl = lifetime_cents // 100
        print('  Lifetime budget setado: R$%d até %s' % (budget_brl, END_TIME[:10]))
        results.append({
            'original_id': cid,
            'original_name': name,
            'new_id': new_id,
            'lifetime_budget_brl': budget_brl,
            'end_time': END_TIME[:10],
            'status': 'OK',
        })

print('\n' + '=' * 60)
print('RESULTADO FINAL:')
for r in results:
    st = r.get('status', '?')
    if st == 'OK':
        print('  ✓ %s → novo ID %s | R$%d total até %s' % (
            r['original_name'], r['new_id'],
            r['lifetime_budget_brl'], r['end_time']))
    else:
        print('  ✗ %s: %s' % (r.get('original_id'), r.get('detalhe', st)))

# Salva IDs para script de pausa das originais
out = __import__('os').path.expanduser('~/.adforge/etapa3_copy_ids.json')
with open(out, 'w') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print('\nIDs salvos em ~/.adforge/etapa3_copy_ids.json')
