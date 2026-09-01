"""
Deploy completo do carrossel 3a Etapa SPID Cup 2026
1. PATCH targeting nos 3 adsets novos (copia do B-00)
2. Upload 11 imagens
3. Cria 3 creatives de carrossel (V1/V2/V3)
4. Cria 3 ads PAUSED (1 por adset)
"""
from pathlib import Path
import os, json, time, urllib.request, urllib.parse, urllib.error

for line in (Path.home() / '.adforge/.env').read_text(encoding='utf-8').splitlines():
    s = line.strip()
    if s and not s.startswith('#') and '=' in s:
        k, _, v = s.partition('=')
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

TOKEN   = os.environ['META_ACCESS_TOKEN']
AD_ACCT = os.environ['META_AD_ACCOUNT_ID']
BASE    = f"https://graph.facebook.com/{os.environ.get('META_API_VERSION','v25.0')}"
PAGE_ID = '102560719007016'
PIXEL   = '867066736318670'

CAROUSEL_DIR = Path(r'E:\SPID-Motor Show\Spid Cup\Eventos-2026\Etapa 3\carrossel-atrações')
TICKET_URL   = 'https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026'

# Adsets novos criados via UI pelo Renato
ADSETS_NOVOS = [
    {'id': '120250369010670761', 'var': 'V1', 'capa': 'PROMODS.png'},
    {'id': '120250369008810761', 'var': 'V2', 'capa': 'SORTEIO-EXCLUSIVO.png'},
    {'id': '120250369014200761', 'var': 'V3', 'capa': 'FESTIVAL-DO-CHURRASCO.png'},
]

VARIACOES = {
    'V1': ['OS-CARROS.png', 'AÇÕES.png', 'ACESSO-LIVRE.png', 'DUAS-PRAÇAS.png',
           'FESTIVAL-DO-CHURRASCO.png', 'LOJAS.png', 'LOUNGE.png',
           'RECREAÇÃO-INFANTIL.png', 'SORTEIO-EXCLUSIVO.png'],
    'V2': ['PROMODS.png', 'OS-CARROS.png', 'AÇÕES.png', 'ACESSO-LIVRE.png',
           'DUAS-PRAÇAS.png', 'FESTIVAL-DO-CHURRASCO.png', 'LOUNGE.png',
           'RECREAÇÃO-INFANTIL.png', 'CRIANÇAS.png'],
    'V3': ['PROMODS.png', 'OS-CARROS.png', 'AÇÕES.png', 'ACESSO-LIVRE.png',
           'DUAS-PRAÇAS.png', 'LOJAS.png', 'LOUNGE.png',
           'CRIANÇAS.png', 'SORTEIO-EXCLUSIVO.png'],
}

CARD_TITLES = {
    'PROMODS.png':              'Pro Mod a 355km/h',
    'OS-CARROS.png':            'Os carros mais rápidos do Brasil',
    'AÇÕES.png':                'Ação ao vivo na pista',
    'ACESSO-LIVRE.png':         'Acesso livre ao paddock',
    'DUAS-PRAÇAS.png':          'Duas praças de alimentação',
    'FESTIVAL-DO-CHURRASCO.png':'Festival do Churrasco',
    'LOJAS.png':                'Lojas e expositores',
    'LOUNGE.png':               'Lounge exclusivo',
    'RECREAÇÃO-INFANTIL.png':   'Recreação infantil',
    'CRIANÇAS.png':             'Diversão para toda a família',
    'SORTEIO-EXCLUSIVO.png':    'Sorteio exclusivo no evento',
}

BODIES = [
    'Quem hesitou: queimou. Individual R$90, Família R$135. SPID Cup 3ª Etapa — 28 a 30/Ago, SPID, Itatiba.',
    'Borrachão feito, pista quente. 4 dias pra largada. Individual R$90, Família R$135 — garanta agora em agendaesportiva.com.br.',
    'Você viu o SPID. É essa semana. Individual R$90, Família R$135. 28/Ago ao vivo — arrancada real de 201m, carros a 355km/h.',
    '201m de pista. Pro Mod a 355km/h. 28/Ago ao vivo. Só existe ao vivo — Individual R$90. SPID, Itatiba/SP.',
    'Volta pra pista. 3ª Etapa SPID Cup — 28 a 30/Ago, Itatiba. Individual R$90, Família R$135. Não existe câmera lenta ao vivo.',
]

def log(msg): print(f'[{time.strftime("%H:%M:%S")}] {msg}', flush=True)

def api_get(path, params=None):
    p = {**(params or {}), 'access_token': TOKEN}
    url = f'{BASE}/{path}?{urllib.parse.urlencode(p)}'
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())

def api_post(path, data):
    payload = {**data, 'access_token': TOKEN}
    req = urllib.request.Request(
        f'{BASE}/{path}',
        data=urllib.parse.urlencode(payload).encode(),
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        return None, err.get('error', {})

def upload_image(fpath):
    stem = fpath.stem
    name = fpath.name
    ct   = 'image/png' if name.lower().endswith('.png') else 'image/jpeg'
    img  = fpath.read_bytes()
    bnd  = '----MetaBnd'
    body = (f'--{bnd}\r\nContent-Disposition: form-data; name="{stem}"; '
            f'filename="{name}"\r\nContent-Type: {ct}\r\n\r\n').encode() \
           + img + f'\r\n--{bnd}--\r\n'.encode()
    url = f'{BASE}/{AD_ACCT}/adimages?access_token={TOKEN}'
    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header('Content-Type', f'multipart/form-data; boundary={bnd}')
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read())
        for _, v in resp.get('images', {}).items():
            return v.get('hash')
    except urllib.error.HTTPError as e:
        err = json.loads(e.read()).get('error', {})
        log(f'  ERRO {name}: {err.get("message")}')
        return None

# ── 1. PATCH targeting nos 3 adsets novos ────────────────────────────────────
log('=== FASE 1: Targeting nos adsets novos ===')
b00 = api_get('120249615946860761', {'fields': 'targeting,promoted_object'})
targeting      = b00.get('targeting', {})
promoted_obj   = b00.get('promoted_object', {'pixel_id': PIXEL, 'custom_event_type': 'PURCHASE'})
log(f'  Targeting B-00 obtido: {len(json.dumps(targeting))} chars')

for a in ADSETS_NOVOS:
    r, err = api_post(a['id'], {
        'targeting':       json.dumps(targeting),
        'promoted_object': json.dumps(promoted_obj),
    })
    if err:
        log(f'  ERR {a["var"]} {a["id"]}: {err.get("message")} (sub={err.get("error_subcode")})')
    else:
        log(f'  OK  {a["var"]} {a["id"]} — targeting aplicado')

# ── 2. Upload 11 imagens ──────────────────────────────────────────────────────
log('\n=== FASE 2: Upload das 11 imagens ===')
hash_map = {}
for img in sorted(CAROUSEL_DIR.glob('*.png')):
    h = upload_image(img)
    if h:
        hash_map[img.name] = h
        log(f'  OK  {img.name} → ...{h[-8:]}')
    else:
        log(f'  SKIP {img.name}')

log(f'  {len(hash_map)}/11 imagens subidas')
if len(hash_map) < 5:
    log('ERRO CRÍTICO: menos de 5 imagens — abortando')
    exit(1)

# ── 3 & 4. Creatives + Ads ────────────────────────────────────────────────────
log('\n=== FASE 3-4: Creatives e Ads ===')
results = []
for i, adset in enumerate(ADSETS_NOVOS):
    var   = adset['var']
    capa  = adset['capa']
    resto = VARIACOES[var]
    body  = BODIES[i % len(BODIES)]

    # Montar cards (max 10: 1 capa + 9 resto)
    ordered = [capa] + resto
    cards = []
    for img_name in ordered:
        h = hash_map.get(img_name)
        if not h:
            log(f'  SKIP card {img_name} — sem hash')
            continue
        cards.append({
            'link':       TICKET_URL,
            'image_hash': h,
            'name':       CARD_TITLES.get(img_name, img_name.replace('.png', '')),
            'description': 'Individual R$90 | Família R$135',
            'call_to_action': {'type': 'SHOP_NOW', 'value': {'link': TICKET_URL}},
        })

    story_spec = {
        'page_id': PAGE_ID,
        'link_data': {
            'message':              body,
            'link':                 TICKET_URL,
            'call_to_action':       {'type': 'SHOP_NOW'},
            'child_attachments':    cards,
            'multi_share_end_card': False,
        },
    }

    # Criar creative
    cr_name = f'[RMKT] Carrossel Atrações {var} — 3ª Etapa SPID Cup 2026'
    cr, cr_err = api_post(f'{AD_ACCT}/adcreatives', {
        'name':                 cr_name,
        'object_story_spec':    json.dumps(story_spec),
        'use_dynamic_creative': 'false',
    })
    if cr_err:
        log(f'  ERR creative {var}: {cr_err.get("message")}')
        results.append({'var': var, 'ok': False, 'err': cr_err.get('message')})
        continue
    cr_id = cr['id']
    log(f'  Creative {var} OK → id={cr_id}')

    # Criar ad PAUSED
    ad_name = f'[RMKT] Carrossel Atrações {var} | {adset["id"][-8:]}'
    ad, ad_err = api_post(f'{AD_ACCT}/ads', {
        'name':      ad_name,
        'adset_id':  adset['id'],
        'creative':  json.dumps({'creative_id': cr_id}),
        'status':    'PAUSED',
        'tracking_specs': json.dumps([{
            'action.type': ['offsite_conversion'],
            'fb_pixel':    [PIXEL],
        }]),
    })
    if ad_err:
        log(f'  ERR ad {var}: {ad_err.get("message")} (sub={ad_err.get("error_subcode")})')
        results.append({'var': var, 'cr_id': cr_id, 'ok': False, 'err': ad_err.get('message')})
    else:
        log(f'  Ad {var} PAUSED → id={ad["id"]}')
        results.append({'var': var, 'cr_id': cr_id, 'ad_id': ad['id'], 'ok': True})

# ── Resumo ────────────────────────────────────────────────────────────────────
print('\n' + '='*60)
log('=== RESUMO FINAL ===')
print(f'  Imagens: {len(hash_map)}/11')
for r in results:
    if r['ok']:
        print(f'  {r["var"]} ✓  creative={r["cr_id"]} | ad={r["ad_id"]} | PAUSED')
    else:
        print(f'  {r["var"]} ✗  {r.get("err")}')
print('\nPróximo passo: Renato ativa os 3 ads no Gerenciador.')
