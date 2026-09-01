"""
patch_all_lote_final.py
PATCH inline nos 5 ads com creative spec completo + textos lote final.
Abordagem inline: creative={spec completo} no payload do ad (sem criar creative separado).
"""
import sys, os, json, requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'daily_analyst'))
from common import load_env

env     = load_env()
TOKEN   = env.get('META_ACCESS_TOKEN', '')
API_VER = env.get('META_API_VERSION', 'v25.0')
BASE    = 'https://graph.facebook.com/%s' % API_VER
PAGE_ID = '102560719007016'

HASHES = [
    '02ff181234b58801041576d248b4759b',  # FAMILIA
    '82e8c374d5e4733f54fede56eecfc819',  # COMPRA-SITE
    '7fba41bd032187f669c28168105febb4',  # var-01
    '5c56959f34cbcd358b9a5b330800a344',  # var-02
]
VIDEOS = [
    {'video_id': '1516974276299351'},
    {'video_id': '2637895769998525'},
]
EXTRA = {
    'ad_formats':           ['AUTOMATIC_FORMAT'],
    'optimization_type':    'REGULAR',
    'call_to_action_types': ['SHOP_NOW'],
    'additional_data':      {'multi_share_end_card': False, 'is_click_to_message': False},
    'reasons_to_shop':      False,
    'shops_bundle':         False,
    'descriptions':         [{'text': ''}],
}

BODIES_PROSP = [
    "Lote 2 do Individual encerrou. Lote Final abriu por R$90 - arquibancada + box, arrancada 28-30/Ago em Itatiba/SP.",
    "Sexta e R$40. Sabado ou domingo e R$90. Passaporte 3 dias R$145. Sao Paulo Int'l Dragway, Itatiba/SP.",
    "R$80 acabou. Individual Lote Final por R$90 - venda antecipada online. Depois so nas bilheterias do SPID.",
    "3a Etapa SPID Cup 2026. 28-30/Agosto, Itatiba/SP. Individual Lote Final R$90. Familia R$135 para 2 pessoas.",
    "355km/h em linha reta. Individual agora R$90 no Lote Final. Venda antecipada fecha 27/Ago.",
    "Familia no SPID Cup: 2 ingressos por R$135. Arquibancada + box, 3 dias de arrancada real. 28 a 30/Ago.",
    "Faltam 13 dias. Individual R$90, Familia R$135. Sao Paulo International Dragway, 28 a 30/Ago.",
]
TITLES_PROSP = [
    "3a Etapa SPID Cup 2026",
    "Lote Final - R$90",
    "28-30/Ago - Itatiba/SP",
    "Individual Lote Final",
    "Ingresso a partir de R$40",
    "SPID Cup - Lote Final",
]

BODIES_RMKT = [
    "Voce viu o SPID. Lote 2 encerrou - Lote Final do Individual no ar por R$90. Fecha agora.",
    "R$80 acabou. Quem ainda nao comprou, o Lote Final do Individual esta por R$90. 28-30/Ago, Itatiba/SP.",
    "Voce ja esteve. Sabe o que esperar. Lote Final por R$90 - vem.",
    "A pista de 201m, o Pro Mod a 355km/h, a galera no box. Individual Lote Final R$90. 28 a 30/Ago.",
    "Lote Final aberto. Individual R$90, Familia R$135 para 2, Passaporte R$145. Antecipado ate 27/Ago.",
    "Ultima chance antecipada. Individual R$90 ate 27/Ago. Depois so bilheteria do SPID.",
    "Faltam 13 dias. Individual R$90, Familia R$135. Sao Paulo International Dragway, 28 a 30/Ago.",
]
TITLES_RMKT = [
    "Lote Final - R$90",
    "Volta pra pista - 3a Etapa SPID Cup",
    "28-30/Ago | Itatiba/SP",
    "Agora e o Lote Final",
    "Individual R$90 - Lote Final",
    "SPID Cup 2026 - Compra ja",
    "Ultima chance antecipada",
]

ADS = [
    {
        'id':       '120249615677680761',
        'name':     'A-01 PROSP',
        'type':     'prosp',
        'link':     'https://spidcup.com.br/spidcup-ingressos/',
        'status':   'ACTIVE',   # status original a restaurar se necessario
    },
    {
        'id':       '120249601960410761',
        'name':     'B-01 Volta pra pista',
        'type':     'rmkt',
        'link':     'https://agendaesportiva.com.br/ingressos_etapa3spidcup2026',
        'status':   'ACTIVE',
    },
    {
        'id':       '120249615979300761',
        'name':     'B-00 Pageview',
        'type':     'rmkt',
        'link':     'https://agendaesportiva.com.br/ingressos_etapa3spidcup2026',
        'status':   'ACTIVE',
    },
    {
        'id':       '120249615985150761',
        'name':     'B-03 InitiateCheckout',
        'type':     'rmkt',
        'link':     'https://agendaesportiva.com.br/ingressos_etapa3spidcup2026',
        'status':   'ACTIVE',
    },
    {
        'id':       '120249615981500761',
        'name':     'B-02 Purchase',
        'type':     'rmkt',
        'link':     'https://agendaesportiva.com.br/ingressos_etapa3spidcup2026',
        'status':   'PAUSED',   # foi pausado no teste anterior — manter PAUSED ate Renato ativar
    },
]


def patch_ad(ad):
    is_prosp = ad['type'] == 'prosp'
    bodies = BODIES_PROSP if is_prosp else BODIES_RMKT
    titles = TITLES_PROSP if is_prosp else TITLES_RMKT

    afs = {
        'images':    [{'hash': h} for h in HASHES],
        'videos':    VIDEOS,
        'bodies':    [{'text': t} for t in bodies],
        'titles':    [{'text': t} for t in titles],
        'link_urls': [{'website_url': ad['link']}],
        **EXTRA,
    }
    creative_spec = {
        'asset_feed_spec':      afs,
        'object_story_spec':    {'page_id': PAGE_ID},
        'use_dynamic_creative': False,
    }
    payload = {
        'creative':     json.dumps(creative_spec),
        'access_token': TOKEN,
    }
    resp = requests.post('%s/%s' % (BASE, ad['id']), data=payload, timeout=60)
    data = resp.json()
    if data.get('success'):
        print('  OK: %s' % ad['name'])
        return True
    print('  ERRO %s: %s' % (ad['name'], json.dumps(data, ensure_ascii=False)[:400]))
    return False


def main():
    print('\n=== PATCH INLINE - LOTE FINAL (5 ads) ===')
    results = []
    for ad in ADS:
        print('\n--- %s ---' % ad['name'])
        ok = patch_ad(ad)
        results.append((ad['name'], 'OK' if ok else 'FALHOU'))

    print('\n=== RESULTADO FINAL ===')
    for name, status in results:
        icon = 'V' if status == 'OK' else 'X'
        print('  [%s] %s' % (icon, name))

    print('\nNOTA: B-02 foi pausado durante os testes. Renato reativa apos revisar.')
    print('Todos os outros ads: status ACTIVE com criativos Lote Final.')


if __name__ == '__main__':
    main()
