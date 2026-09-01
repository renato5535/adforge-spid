"""
Pausa as duas campanhas ORIGINAIS da 3ª Etapa após confirmação de que
as cópias (com lifetime budget) estão ativas e entregando.
Execute SOMENTE após Renato publicar as campanhas novas.
"""
import sys, json, requests
sys.path.insert(0, __import__('os').path.expanduser('~/.adforge/daily_analyst'))
from common import load_env

env     = load_env()
token   = env.get('META_ACCESS_TOKEN', '')
api_ver = env.get('META_API_VERSION', 'v25.0')
BASE    = 'https://graph.facebook.com/%s' % api_ver

ORIGINAIS = [
    ('120249458187670761', '[PROSPECTO][CONVERSÃO] 3ª Etapa SPID Cup 2026'),
    ('120249458187120761', '[RMKT][CONVERSÃO] 3ª Etapa SPID Cup 2026'),
]
NOVAS = [
    ('120249601369080761', '[PROSPECTO] 3ª Etapa [COPIA]'),
    ('120249601416320761', '[RMKT] 3ª Etapa [COPIA]'),
]

print('Verificando status das campanhas novas antes de pausar originais...')
for cid, name in NOVAS:
    r = requests.get('%s/%s' % (BASE, cid),
        params={'fields': 'id,name,effective_status', 'access_token': token})
    c = r.json()
    st = c.get('effective_status', '?')
    print('  %s → status: %s' % (name, st))
    if st != 'ACTIVE':
        print('\n  ⚠️  ATENÇÃO: campanha nova ainda não está ACTIVE.')
        print('  Publique as campanhas novas no Gerenciador antes de rodar este script.')
        sys.exit(1)

print('\nCampanhas novas ATIVAS. Pausando originais...')
for cid, name in ORIGINAIS:
    r = requests.post('%s/%s' % (BASE, cid),
        data={'status': 'PAUSED', 'access_token': token})
    resp = r.json()
    if resp.get('success') or resp.get('id'):
        print('  PAUSADA: %s' % name)
    else:
        print('  ERRO pausando %s: %s' % (name, resp.get('error', {}).get('message', str(resp))))

print('\nPronto. Campanhas originais pausadas.')
