"""
PATCH dos 4 ads ativos da 3a Etapa com o criativo INGRESSO-BILHETERIA.
Usa inline creative spec (padrao estabelecido).
"""
import sys, os, json
import requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'daily_analyst'))
from common import load_env

env     = load_env()
TOKEN   = env.get('META_ACCESS_TOKEN', '')
API_VER = env.get('META_API_VERSION', 'v25.0')
BASE    = f'https://graph.facebook.com/{API_VER}'
PAGE_ID = '102560719007016'

IMAGE_HASH = 'fe53077340669f98aa2a7951778d20b1'  # INGRESSO-BILHETERIA.png

# AD_ID → URL atual (preservar URL de cada campanha)
ADS = [
    {
        'id':      '120249615979300761',
        'name':    'B-00 Pageview 180D',
        'prefix':  'RMKT',
        'url':     'https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026',
    },
    {
        'id':      '120249601960410761',
        'name':    'B-01 Video View 95%',
        'prefix':  'RMKT',
        'url':     'https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026',
    },
    {
        'id':      '120249615981500761',
        'name':    'B-02 Purchase 180D',
        'prefix':  'RMKT',
        'url':     'https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026',
    },
    {
        'id':      '120249615677680761',
        'name':    'A-01 LKL 1% Purchase',
        'prefix':  'PROSP',
        'url':     None,  # buscar ao vivo
    },
]

BODIES = [
    'O Agenda Esportiva ficou fora no fim de semana. A 3ª Etapa não mudou: 28, 29 e 30 de agosto no SPID, Itatiba/SP.\n\nBilheteria presencial aberta nos 3 dias. Você chega, paga e assiste ao vivo carros que percorrem 201 metros em menos de 4 segundos. Só precisa do documento — nada pra imprimir.',
    'Tentou comprar no site e não conseguiu? Tem bilheteria.\n\n28, 29 e 30 de agosto no SPID, Itatiba/SP. Sem reserva antecipada. Os Pro Mods saem a mais de 300 km/h. Você ainda tem tempo de ver ao vivo.',
    'Bilheteria presencial aberta. 3 dias de evento.\n\nSe o site te freou, não deixa o evento te frear também. A 3ª Etapa SPID Cup acontece 28 a 30 de agosto no SPID, Itatiba/SP. Bilheteria no local, sem reserva antecipada. Chega, paga e entra.',
]

TITLES = [
    'Site travou? Bilheteria tá aberta',
    'Bilheteria presencial — 28 a 30/Ago',
    '3 dias. Bilheteria aberta no SPID',
]

# Buscar URL do A-01 ao vivo
print('Buscando URL do A-01...')
resp = requests.get(
    f"{BASE}/120249615677680761",
    params={'fields': 'creative{asset_feed_spec}', 'access_token': TOKEN},
    timeout=20
)
a01_creative = resp.json().get('creative', {})
a01_afs = a01_creative.get('asset_feed_spec', {})
a01_links = a01_afs.get('link_urls', [{}])
a01_url = a01_links[0].get('website_url', 'https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026') if a01_links else 'https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026'
ADS[3]['url'] = a01_url
print(f'  A-01 URL: {a01_url}')

print('\nAplicando PATCH nos 4 ads...\n')

for ad in ADS:
    afs = {
        'images':               [{'hash': IMAGE_HASH}],
        'bodies':               [{'text': b} for b in BODIES],
        'titles':               [{'text': t} for t in TITLES],
        'descriptions':         [{'text': ''}],
        'link_urls':            [{'website_url': ad['url']}],
        'ad_formats':           ['AUTOMATIC_FORMAT'],
        'optimization_type':    'REGULAR',
        'call_to_action_types': ['SHOP_NOW'],
        'additional_data':      {'multi_share_end_card': False, 'is_click_to_message': False},
        'reasons_to_shop':      False,
        'shops_bundle':         False,
    }
    creative_spec = {
        'asset_feed_spec':     afs,
        'object_story_spec':   {'page_id': PAGE_ID},
        'use_dynamic_creative': False,
    }
    payload = {
        'creative':     json.dumps(creative_spec),
        'access_token': TOKEN,
    }
    resp2 = requests.post(f"{BASE}/{ad['id']}", data=payload, timeout=30)
    r = resp2.json()
    if resp2.status_code == 200 and r.get('success'):
        print(f'  OK  [{ad["prefix"]}] {ad["name"]}')
    else:
        err = r.get('error', {})
        print(f'  ERR [{ad["prefix"]}] {ad["name"]}')
        print(f'       msg={err.get("message")} | subcode={err.get("error_subcode")}')

print('\nDone. Criativos trocados — ads continuam no mesmo status (ativo/pausado).')
print('Nenhum status foi alterado (conforme padrao: omitir status no PATCH).')
