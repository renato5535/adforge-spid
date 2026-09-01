"""
patch_inline_creative.py
Tenta PATCH no ad com creative spec completo inline (sem criar creative separado).
"""
import sys, os, json, requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'daily_analyst'))
from common import load_env

env    = load_env()
TOKEN  = env.get('META_ACCESS_TOKEN', '')
API_VER = env.get('META_API_VERSION', 'v25.0')
BASE   = 'https://graph.facebook.com/%s' % API_VER
PAGE_ID = '102560719007016'

HASHES = [
    '02ff181234b58801041576d248b4759b',
    '82e8c374d5e4733f54fede56eecfc819',
    '7fba41bd032187f669c28168105febb4',
    '5c56959f34cbcd358b9a5b330800a344',
]
VIDEOS = [
    {'video_id': '1516974276299351'},
    {'video_id': '2637895769998525'},
]
BODIES_RMKT = [
    "Voce viu o SPID. Lote 2 encerrou - Lote Final do Individual no ar por R$90. Fecha agora.",
    "R$80 acabou. Lote Final do Individual esta por R$90. 28-30/Ago, Itatiba/SP.",
    "Voce ja esteve. Sabe o que esperar. Lote Final por R$90 - vem.",
    "A pista de 201m, o Pro Mod a 355km/h. Individual Lote Final R$90. 28 a 30/Ago.",
    "Lote Final aberto. Individual R$90, Familia R$135 para 2. Ate 27/Ago.",
]
TITLES_RMKT = [
    "Lote Final - R$90",
    "Volta pra pista - 3a Etapa SPID Cup",
    "28-30/Ago | Itatiba/SP",
    "Individual R$90 - Lote Final",
    "SPID Cup 2026 - Ultima chance",
]

# Testar apenas B-02 primeiro
AD_ID = '120249615981500761'
LINK  = 'https://agendaesportiva.com.br/ingressos_etapa3spidcup2026'

afs = {
    'images':              [{'hash': h} for h in HASHES],
    'videos':              VIDEOS,
    'bodies':              [{'text': t} for t in BODIES_RMKT],
    'titles':              [{'text': t} for t in TITLES_RMKT],
    'descriptions':        [{'text': ''}],
    'link_urls':           [{'website_url': LINK}],
    'ad_formats':          ['AUTOMATIC_FORMAT'],
    'optimization_type':   'REGULAR',
    'call_to_action_types': ['SHOP_NOW'],
    'additional_data':     {'multi_share_end_card': False, 'is_click_to_message': False},
    'reasons_to_shop':     False,
    'shops_bundle':        False,
}

creative_spec = {
    'asset_feed_spec':   afs,
    'object_story_spec': {'page_id': PAGE_ID},
    'use_dynamic_creative': False,
}

payload = {
    'creative':     json.dumps(creative_spec),
    'access_token': TOKEN,
}

resp = requests.post('%s/%s' % (BASE, AD_ID), data=payload, timeout=30)
print(json.dumps(resp.json(), ensure_ascii=False, indent=2)[:800])
