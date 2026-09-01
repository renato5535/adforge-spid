"""
patch_creative_direct.py
Atualiza os creatives existentes diretamente (PATCH no creative, nao no ad).
Approach alternativo quando PATCH no ad falha com 2446391.
"""
import sys, os, json, requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'daily_analyst'))
from common import load_env

env     = load_env()
TOKEN   = env.get('META_ACCESS_TOKEN', '')
API_VER = env.get('META_API_VERSION', 'v25.0')
BASE    = 'https://graph.facebook.com/%s' % API_VER

# Hashes finais (já subidos)
HASHES = [
    '02ff181234b58801041576d248b4759b',  # FAMÍLIA
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
    "Familia no SPID Cup: 2 ingressos por R$135. Arquibancada + box, 3 dias de arrancada real. 28 a 30/Ago, Itatiba.",
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

# creative_id -> (tipo, link_url)
CREATIVES = [
    ('2080187645918658',  'prosp', 'https://spidcup.com.br/spidcup-ingressos/'),
    ('1090931196689060',  'rmkt',  'https://agendaesportiva.com.br/ingressos_etapa3spidcup2026'),
    ('2800772793656801',  'rmkt',  'https://agendaesportiva.com.br/ingressos_etapa3spidcup2026'),
    ('1358223132597703',  'rmkt',  'https://agendaesportiva.com.br/ingressos_etapa3spidcup2026'),
    ('2216881612407780',  'rmkt',  'https://agendaesportiva.com.br/ingressos_etapa3spidcup2026'),
]


def patch_creative(cr_id, tipo, link_url):
    bodies = BODIES_PROSP if tipo == 'prosp' else BODIES_RMKT
    titles = TITLES_PROSP if tipo == 'prosp' else TITLES_RMKT

    afs = {
        'images':    [{'hash': h} for h in HASHES],
        'videos':    VIDEOS,
        'bodies':    [{'text': t} for t in bodies],
        'titles':    [{'text': t} for t in titles],
        'link_urls': [{'website_url': link_url}],
        **EXTRA,
    }

    url = '%s/%s' % (BASE, cr_id)
    payload = {
        'name':            'LoteFinal-%s-%s' % (tipo, cr_id[-6:]),
        'asset_feed_spec': json.dumps(afs),
        'access_token':    TOKEN,
    }
    resp = requests.post(url, data=payload, timeout=30)
    data = resp.json()
    if data.get('success'):
        print('  OK: creative %s atualizado' % cr_id)
        return True
    print('  ERRO %s: %s' % (cr_id, json.dumps(data, ensure_ascii=False)[:300]))
    return False


def main():
    print('\n=== PATCH DIRETO NOS CREATIVES ===')
    for cr_id, tipo, link_url in CREATIVES:
        print('\n--- creative %s (%s) ---' % (cr_id, tipo))
        patch_creative(cr_id, tipo, link_url)


if __name__ == '__main__':
    main()
