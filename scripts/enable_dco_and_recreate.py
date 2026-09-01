#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Habilita DCO nos adsets e recria criativos com asset_feed_spec
(5 textos + 5 títulos + descrição). Padrão definitivo AdForge.
"""

import os, json, time, sys
import requests

# ── Env ──────────────────────────────────────────────────────────────────────
env = {}
with open(os.path.expanduser('~/.adforge/.env')) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            env[k.strip()] = v.strip()

TOKEN   = env['META_ACCESS_TOKEN']
ACCOUNT = 'act_881694943239418'
PAGE_ID = '102560719007016'
VER     = 'v25.0'
BASE    = f'https://graph.facebook.com/{VER}'

URLS = {
    'PROSPECTO': 'https://spidcup.com.br/spidcup-ingressos/',
    'RMKT':      'https://agendaesportiva.com.br/ingressos_etapa3spidcup2026'
}

CAMPS = {
    'PROSPECTO': '120249458187670761',
    'RMKT':      '120249458187120761'
}

ADSETS = {
    'PROSPECTO': [
        ('120249458543460761', 'A-02 Engajamento 365D'),
        ('120249458542640761', 'A-01 LKL 1% Purchase 180D'),
    ],
    'RMKT': [
        ('120249458541220761', 'B-03 InitiateCheckout 180D'),
        ('120249458540310761', 'B-02 Purchase 180D'),
        ('120249458539200761', 'B-01 Video View 95% 180D'),
        ('120249458523540761', 'B-00 Pageview 180D'),
    ],
}

# ── Copies ───────────────────────────────────────────────────────────────────
TEXTS_P = [
    (
        "Existe uma pista em Itatiba onde carros batem 355km/h em 201 metros.\n\n"
        "É arrancada. É SPID Cup.\n\n"
        "3ª Etapa: 28 a 30 de agosto de 2026.\n"
        "São Paulo International Dragway, Itatiba/SP.\n\n"
        "Ingresso a partir de R$70. Família por R$105. Parcelado em 12x."
    ),
    (
        "Evento de automobilismo em que o filho fica encantado, o pai fica emocionado e a mãe filma tudo.\n\n"
        "Arquibancada + acesso livre aos boxes. Crianças até 10 anos entram de graça.\n\n"
        "3ª Etapa SPID Cup — 28 a 30 de agosto, Itatiba/SP.\n\n"
        "Ingresso família: R$105 (Lote 1, só online e antecipado).\n"
        "Parcelado em até 12x no cartão."
    ),
    (
        "Arquibancada. Boxes abertos. Os carros mais rápidos do Brasil passando pertinho.\n\n"
        "Três dias de arrancada em Itatiba — sexta, sábado e domingo.\n\n"
        "SPID Cup, 3ª Etapa — 28 a 30 de agosto.\n\n"
        "Ingresso individual: R$70 (Lote 1).\n"
        "Passaporte 3 dias: R$120 (50 unidades)."
    ),
    (
        "Dois carros. Uma largada. O mais rápido vence.\n\n"
        "Você assiste tudo pertinho da pista.\n\n"
        "SPID Cup — São Paulo International Dragway, Itatiba/SP.\n"
        "3ª Etapa: 28 a 30 de agosto.\n\n"
        "Ingresso: R$70/dia."
    ),
    (
        "9 de agosto é Dia dos Pais.\n\n"
        "Se o pai é do tipo que gosta de motor e velocidade, o presente está neste link.\n\n"
        "3ª Etapa SPID Cup — 28 a 30 de agosto em Itatiba/SP.\n\n"
        "Ingresso família (pai + alguém especial): R$105 no Lote 1.\n"
        "Crianças até 10 anos: de graça.\n"
        "Parcelado em 12x."
    ),
]

TEXTS_R = [
    (
        "Você visitou. Curtiu. O Lote 1 tá acabando.\n\n"
        "R$70 a entrada diária (sábado ou domingo) pra você dentro da arquibancada do SPID, "
        "com acesso livre aos boxes.\n\n"
        "28 a 30 de agosto — São Paulo International Dragway, Itatiba.\n\n"
        "Parcelado em até 12x no cartão."
    ),
    (
        "Passaporte 3 dias por R$120.\n\n"
        "Sexta, sábado e domingo no SPID — livre pra entrar, sair e voltar quando quiser.\n\n"
        "50 unidades no total. Quando esgotar, acabou.\n\n"
        "Ingresso família por R$105 também disponível (só online, só antecipado).\n\n"
        "3ª Etapa SPID Cup — 28 a 30/Ago, Itatiba."
    ),
    (
        "Você já sentiu o chão tremer quando os pilotos aceleram.\n\n"
        "Essa sensação volta dia 28 de agosto.\n\n"
        "3ª Etapa SPID Cup em Itatiba.\n\n"
        "Ingresso: R$70 (Lote 1).\n"
        "Família: R$105 (Lote 1, só online).\n"
        "Crianças até 10 anos: de graça."
    ),
    (
        "Quem ficou do lado de fora sabe o que tá perdendo.\n\n"
        "Lounge SPID: área coberta na cabeceira da pista, open bar de 11h às 16h "
        "(chopp, refrigerante, água), mini-pizza, fritas, mini-burger, "
        "transmissão ao vivo by Hot 402, copo personalizado.\n\n"
        "2 dias (sáb + dom): R$450.\n"
        "1 dia: R$299.\n\n"
        "10 unidades por evento."
    ),
    (
        "Ingresso de sábado ou domingo no SPID.\n\n"
        "Individual: R$70 (Lote 1).\n"
        "Família: R$105 (Lote 1).\n"
        "Passaporte 3 dias: R$120 (50 vagas).\n\n"
        "Crianças até 10 anos entram de graça.\n"
        "Estudantes, idosos e PcD: meia-entrada.\n\n"
        "Parcelado em até 12x. Só antecipado online — bilheteria nos dias do evento "
        "não garante Lote 1."
    ),
]

HEADLINES_P = [
    "355km/h em Itatiba, 28/Ago",
    "Família por R$105 — só online",
    "Os carros mais rápidos do Brasil",
    "Crianças até 10 anos: de graça",
    "O presente do Dia dos Pais",
]

HEADLINES_R = [
    "Lote 1: R$70 por dia",
    "Família por R$105 — só online",
    "Passaporte 3 dias: R$120",
    "SPID Cup — 28 a 30/Ago",
    "Lounge SPID: R$299/dia",
]

COPY = {
    'PROSPECTO': {'texts': TEXTS_P, 'headlines': HEADLINES_P, 'desc': 'Ingresso individual a partir de R$70.'},
    'RMKT':      {'texts': TEXTS_R, 'headlines': HEADLINES_R, 'desc': '12x no cartão. Crianças até 10 anos entram grátis.'},
}

# ── API helpers ───────────────────────────────────────────────────────────────
def post(endpoint, data):
    data = dict(data)
    data['access_token'] = TOKEN
    r = requests.post(f'{BASE}/{endpoint}', json=data)
    return r.json()

def get_ads(camp_id):
    fields = 'id,name,status,creative{id,object_type,object_story_spec}'
    ads, url = [], f'{BASE}/{camp_id}/ads'
    params = {'fields': fields, 'limit': 50, 'access_token': TOKEN}
    while url:
        r = requests.get(url, params=params).json()
        ads.extend(r.get('data', []))
        url = r.get('paging', {}).get('next')
        params = {}
    return ads

# ── DCO enable ────────────────────────────────────────────────────────────────
def enable_dco(adset_id, name):
    r = post(adset_id, {'is_dynamic_creative': True})
    if r.get('success'):
        print(f"  ✅ DCO ON → {name} ({adset_id})")
        return True
    msg = r.get('error', {}).get('message', str(r))[:90]
    print(f"  ❌ {name}: {msg}")
    return False

# ── Creative builders ─────────────────────────────────────────────────────────
def build_feed(camp_type, image_hash=None, video_id=None, thumb_hash=None):
    c   = COPY[camp_type]
    url = URLS[camp_type]
    feed = {
        'bodies':               [{'text': t} for t in c['texts']],
        'titles':               [{'text': h} for h in c['headlines']],
        'descriptions':         [{'text': c['desc']}],
        'call_to_action_types': ['SHOP_NOW'],
        'link_urls':            [{'website_url': url}],
    }
    if image_hash:
        feed['images'] = [{'hash': image_hash}]
    else:
        feed['videos'] = [{'video_id': video_id, 'thumbnail_hash': thumb_hash}]
    return feed

def create_dco_image(camp_type, image_hash):
    url = URLS[camp_type]
    feed = build_feed(camp_type, image_hash=image_hash)
    feed['ad_formats'] = ['SINGLE_IMAGE']
    payload = {
        'name': f'[{camp_type}] img-{image_hash[:8]}-DCO',
        'object_story_spec': {'page_id': PAGE_ID},
        'asset_feed_spec': feed,
    }
    r = post(f'{ACCOUNT}/adcreatives', payload)
    if 'id' in r:
        return r['id']
    print(f"    ❌ img DCO: {r.get('error', {}).get('message', '?')[:90]}")
    return None

def create_dco_video(camp_type, video_id, thumb_hash):
    url = URLS[camp_type]
    feed = build_feed(camp_type, video_id=video_id, thumb_hash=thumb_hash)
    feed['ad_formats'] = ['SINGLE_VIDEO']
    payload = {
        'name': f'[{camp_type}] vid-{str(video_id)[-6:]}-DCO',
        'object_story_spec': {'page_id': PAGE_ID},
        'asset_feed_spec': feed,
    }
    r = post(f'{ACCOUNT}/adcreatives', payload)
    if 'id' in r:
        return r['id']
    print(f"    ❌ vid DCO: {r.get('error', {}).get('message', '?')[:90]}")
    return None

# ═══════════════════════════════════════════════════════════════════════════════
# DCO já habilitado em 6/6 adsets — apenas criar criativos + atualizar ads
# ═══════════════════════════════════════════════════════════════════════════════
dco_ok = 6
print("\n" + "="*60)
print("  Criativos DCO (5 textos + 5 títulos) + atualizar ads")
print("="*60)

ok = fail = 0
log = []

for camp_type, camp_id in CAMPS.items():
    print(f"\n[{camp_type}] URL={URLS[camp_type]}")
    ads = get_ads(camp_id)
    print(f"  {len(ads)} ads")
    cache = {}

    for ad in ads:
        c   = ad.get('creative', {})
        oss = c.get('object_story_spec', {})
        ld  = oss.get('link_data',  {})
        vd  = oss.get('video_data', {})

        if ld:
            img_hash = ld.get('image_hash', '')
            key = f'img:{img_hash}'
        elif vd:
            vid_id = vd.get('video_id', '')
            thumb  = vd.get('image_hash', '')
            key = f'vid:{vid_id}'
        else:
            print(f"  ⚠️  SKIP {ad['id']}: tipo desconhecido")
            continue

        if key not in cache:
            print(f"\n  Criativo DCO → {key[:22]}")
            if ld:
                cid = create_dco_image(camp_type, img_hash)
            else:
                cid = create_dco_video(camp_type, vid_id, thumb)
            cache[key] = cid
            print(f"  {'✅ ' + cid if cid else '❌ Falhou'}")

        cid = cache[key]
        if not cid:
            fail += 1
            log.append({'status': 'FAIL_CREATE', 'ad': ad['id']})
            continue

        r = post(ad['id'], {'creative': {'creative_id': cid}})
        if r.get('success'):
            ok += 1
            print(f"  ✅ {ad['id']} | {ad['name'][:48]}")
            log.append({'status': 'OK', 'ad': ad['id'], 'creative': cid})
        else:
            fail += 1
            err = r.get('error', {}).get('message', str(r))[:80]
            print(f"  ❌ {ad['id']}: {err}")
            log.append({'status': 'FAIL_UPDATE', 'ad': ad['id'], 'error': err})

        time.sleep(0.3)

# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print(f"  RESULTADO: {ok} atualizados  |  {fail} falhas")
print(f"  DCO ativo: {dco_ok}/6 adsets")
print("="*60)

with open(os.path.expanduser('~/.adforge/logs/dco_result.json'), 'w', encoding='utf-8') as f:
    json.dump({'dco_adsets': dco_ok, 'ads_ok': ok, 'ads_fail': fail, 'log': log}, f, ensure_ascii=False, indent=2)
print("  Log → ~/.adforge/logs/dco_result.json")
sys.exit(0 if fail == 0 else 1)
