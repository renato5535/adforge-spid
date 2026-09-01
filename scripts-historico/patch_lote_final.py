"""
patch_lote_final.py
Troca criativos do lote 2 para lote final nos 5 ads ativos da 3ª Etapa.

Operações:
  1. Upload de COMPRA-SITE-var-01.png e COMPRA-SITE-var-02.png
  2. Para cada ad ativo: novo creative com imagens + textos do lote final
  3. PATCH no ad com o novo creative_id

Hashes mantidos:
  82e8c374d5e4733f54fede56eecfc819  = COMPRA-SITE.png
  02ff181234b58801041576d248b4759b  = FAMÍLIA - PARA 2 PESSOAS.png

Hashes removidos (lote 2 + faltam):
  b1a0e236af38cc129103704010e259f1  = 05-INDIVIDUAL-2LOTE-R80.png
  14ef326b760c4a13b1e6f0bb50842f41  = 06-SEXTA-MEIO-INGRESSO-R40.png
  62a90f4c1c4298b807e3becd60bf65bd  = FALTAM-15-DIAS.png
"""
import sys, os, json, requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'daily_analyst'))
from common import load_env, http_get_json

env     = load_env()
TOKEN   = env.get('META_ACCESS_TOKEN', '')
API_VER = env.get('META_API_VERSION', 'v25.0')
ACCOUNT = env.get('META_AD_ACCOUNT_ID', 'act_881694943239418')
PAGE_ID = env.get('META_PAGE_ID', '')

BASE = 'https://graph.facebook.com/%s' % API_VER

# ── Hashes ──────────────────────────────────────────────────────────────────
KEEP_HASHES = {
    '82e8c374d5e4733f54fede56eecfc819',   # COMPRA-SITE
    '02ff181234b58801041576d248b4759b',   # FAMÍLIA
}
REMOVE_HASHES = {
    'b1a0e236af38cc129103704010e259f1',   # 05-INDIVIDUAL-2LOTE-R80
    '14ef326b760c4a13b1e6f0bb50842f41',   # 06-SEXTA-MEIO-INGRESSO-R40
    '62a90f4c1c4298b807e3becd60bf65bd',   # FALTAM-15-DIAS
}

# ── Novas imagens para upload ─────────────────────────────────────────────
IMG_DIR    = r'E:\SPID-Motor Show\Spid Cup\Eventos-2026\Etapa 3'
NEW_IMAGES = [
    'COMPRA-SITE-var-01.png',
    'COMPRA-SITE-var-02.png',
]

# ── Textos lote final ─────────────────────────────────────────────────────
BODIES_PROSP = [
    "Lote 2 do Individual encerrou. Lote Final abriu por R$90 — arquibancada + box, arrancada 28-30/Ago em Itatiba/SP. Quem compra antecipado nao paga bilheteria.",
    "Sexta e R$40. Sabado ou domingo e R$90. Passaporte 3 dias R$145. Sao Paulo Int'l Dragway, Itatiba/SP.",
    "R$80 acabou. Individual Lote Final por R$90 — venda antecipada online. Depois so nas bilheterias do SPID.",
    "3a Etapa SPID Cup 2026. 28-30/Agosto, Itatiba/SP. Individual Lote Final R$90. Familia R$135 para 2 pessoas.",
    "355km/h em linha reta. Individual agora R$90 no Lote Final. Venda antecipada fecha 27/Ago.",
]
TITLES_PROSP = [
    "3a Etapa SPID Cup 2026",
    "Lote Final - R$90",
    "28-30/Ago - Itatiba/SP",
    "Individual Lote Final",
    "Ingresso a partir de R$40",
    "SPID Cup — Lote Final",
]

BODIES_RMKT = [
    "Voce viu o SPID. Lote 2 encerrou — Lote Final do Individual no ar por R$90. Fecha agora.",
    "R$80 acabou. Quem ainda nao comprou, o Lote Final do Individual esta por R$90. 28-30/Ago, Itatiba/SP.",
    "Voce ja esteve. Sabe o que esperar. Lote Final por R$90 — vem.",
    "Lote Final aberto. Individual R$90, Familia R$135 para 2, Passaporte R$145. Antecipado ate 27/Ago.",
    "Ultima chance antecipada. Individual R$90 ate 27/Ago. Depois so bilheteria do SPID.",
]
TITLES_RMKT = [
    "Lote Final - R$90",
    "Volta pra pista - 3a Etapa SPID Cup",
    "28-30/Ago | Itatiba/SP",
    "Agora e o Lote Final",
    "Individual R$90 — Lote Final",
    "SPID Cup 2026 — Compra ja",
    "Ultima chance antecipada",
]

# ── Ads ativos ───────────────────────────────────────────────────────────
ADS = [
    {
        'id': '120249615677680761',
        'name': '[PROSP] 3aEtapa A-01 LKL v2',
        'creative_id': '2080187645918658',
        'link_url': 'https://spidcup.com.br/spidcup-ingressos/',
        'type': 'prosp',
    },
    {
        'id': '120249601960410761',
        'name': '[RMKT] Volta pra pista — 3a Etapa | Lote Final',
        'creative_id': '1090931196689060',
        'link_url': 'https://agendaesportiva.com.br/ingressos_etapa3spidcup2026',
        'type': 'rmkt',
    },
    {
        'id': '120249615979300761',
        'name': '[RMKT] 3aEtapa B-00 Pageview 180D | auto',
        'creative_id': '2800772793656801',
        'link_url': 'https://agendaesportiva.com.br/ingressos_etapa3spidcup2026',
        'type': 'rmkt',
    },
    {
        'id': '120249615985150761',
        'name': '[RMKT] 3aEtapa B-03 InitiateCheckout 180D | auto',
        'creative_id': '1358223132597703',
        'link_url': 'https://agendaesportiva.com.br/ingressos_etapa3spidcup2026',
        'type': 'rmkt',
    },
    {
        'id': '120249615981500761',
        'name': '[RMKT] 3aEtapa B-02 Purchase 180D | auto',
        'creative_id': '2216881612407780',
        'link_url': 'https://agendaesportiva.com.br/ingressos_etapa3spidcup2026',
        'type': 'rmkt',
    },
]

VIDEO_ID = '1516974276299351'


def upload_image(filepath):
    stem = os.path.splitext(os.path.basename(filepath))[0]
    url = '%s/%s/adimages' % (BASE, ACCOUNT)
    with open(filepath, 'rb') as f:
        files = {stem: (os.path.basename(filepath), f, 'image/png')}
        resp = requests.post(url, params={'access_token': TOKEN}, files=files, timeout=120)
    data = resp.json()
    if 'images' in data:
        for k, v in data['images'].items():
            print('  Upload OK: %s => hash=%s' % (stem, v.get('hash')))
            return v.get('hash')
    print('  Upload ERRO:', data)
    return None


def create_creative(ad, image_hashes):
    is_prosp = ad['type'] == 'prosp'
    bodies = BODIES_PROSP if is_prosp else BODIES_RMKT
    titles = TITLES_PROSP if is_prosp else TITLES_RMKT

    afs = {
        'images':              [{'hash': h} for h in image_hashes],
        'videos':              [{'video_id': VIDEO_ID}],
        'bodies':              [{'text': t} for t in bodies],
        'titles':              [{'text': t} for t in titles],
        'descriptions':        [{'text': ''}],
        'link_urls':           [{'website_url': ad['link_url']}],
        'ad_formats':          ['AUTOMATIC_FORMAT'],
        'optimization_type':   'REGULAR',
        'call_to_action_types': ['SHOP_NOW'],
    }

    payload = {
        'name':                 ad['name'] + ' | Lote Final',
        'asset_feed_spec':      json.dumps(afs),
        'use_dynamic_creative': 'false',
        'object_story_spec':    json.dumps({'page_id': PAGE_ID}),
        'access_token':         TOKEN,
    }

    url = '%s/%s/adcreatives' % (BASE, ACCOUNT)
    resp = requests.post(url, data=payload)
    data = resp.json()
    if 'id' in data:
        print('  Creative criado: %s' % data['id'])
        return data['id']
    print('  Creative ERRO:', json.dumps(data, ensure_ascii=False)[:300])
    return None


def patch_ad(ad_id, creative_id):
    url = '%s/%s' % (BASE, ad_id)
    payload = {
        'creative':     json.dumps({'id': creative_id}),
        'access_token': TOKEN,
    }
    resp = requests.post(url, data=payload)
    data = resp.json()
    if data.get('success') or data.get('id'):
        print('  PATCH OK: ad %s' % ad_id)
        return True
    print('  PATCH ERRO:', json.dumps(data, ensure_ascii=False)[:300])
    return False


def main():
    print('\n=== PASSO 1: Upload de imagens novas ===')
    new_hashes = []
    for fname in NEW_IMAGES:
        fpath = os.path.join(IMG_DIR, fname)
        if not os.path.exists(fpath):
            print('  ARQUIVO NAO ENCONTRADO:', fpath)
            continue
        h = upload_image(fpath)
        if h:
            new_hashes.append(h)

    if not new_hashes:
        print('Nenhuma imagem nova subida — abortando.')
        sys.exit(1)

    # Hashes finais: manter + novos
    final_hashes = list(KEEP_HASHES) + new_hashes
    print('\nHashes finais nos ads (%d): %s' % (len(final_hashes), final_hashes))

    print('\n=== PASSO 2: Atualizar ads ===')
    results = []
    for ad in ADS:
        print('\n--- %s ---' % ad['name'])
        creative_id = create_creative(ad, final_hashes)
        if not creative_id:
            results.append((ad['name'], 'FALHOU_CREATIVE'))
            continue
        ok = patch_ad(ad['id'], creative_id)
        results.append((ad['name'], 'OK' if ok else 'FALHOU_PATCH'))

    print('\n=== RESULTADO FINAL ===')
    for name, status in results:
        print('  [%s] %s' % (status, name))


if __name__ == '__main__':
    main()
