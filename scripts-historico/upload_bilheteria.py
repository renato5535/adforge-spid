"""
Upload INGRESSO-BILHETERIA.png e cria ad PAUSED em cada adset ativo da 3a Etapa.
"""
import os, json, urllib.request, urllib.parse
import mimetypes
import uuid
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

token = os.getenv('META_ACCESS_TOKEN')
ad_account = os.getenv('META_AD_ACCOUNT_ID')
page_id = '102560719007016'
image_path = r'E:\SPID-Motor Show\Spid Cup\Eventos-2026\Etapa 3\INGRESSO-BILHETERIA.png'

ADSETS = [
    {'id': '120249615946860761', 'name': 'B-00 Pageview 180D',               'prefix': 'RMKT'},
    {'id': '120249601941100761', 'name': 'B-01 Video View 95% 180D — Cópia', 'prefix': 'RMKT'},
    {'id': '120249615953090761', 'name': 'B-02 Purchase 180D',               'prefix': 'RMKT'},
    {'id': '120249615428170761', 'name': 'A-01 LKL 1% Purchase 180D',        'prefix': 'PROSP'},
]

LINK_URL = 'https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026'

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


# ── 1. Upload da imagem ────────────────────────────────────────────────────────
print('1. Fazendo upload da imagem...')

with open(image_path, 'rb') as f:
    image_data = f.read()

boundary = uuid.uuid4().hex
stem = os.path.splitext(os.path.basename(image_path))[0]

body_parts = []
body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="filename"; filename="{stem}.png"\r\nContent-Type: image/png\r\n\r\n'.encode())
body_parts.append(image_data)
body_parts.append(f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="name"\r\n\r\n{stem}\r\n--{boundary}--\r\n'.encode())
body = b''.join(body_parts)

upload_url = f'https://graph.facebook.com/v25.0/{ad_account}/adimages?access_token={token}'
req = urllib.request.Request(
    upload_url,
    data=body,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
    method='POST'
)
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())

images = result.get('images', {})
image_hash = None
for key, val in images.items():
    image_hash = val.get('hash')
    print(f'   hash={image_hash} | name={val.get("name")}')
    break

if not image_hash:
    print('ERRO: upload falhou')
    print(json.dumps(result, indent=2))
    exit(1)

print(f'   Upload OK — hash={image_hash}')


# ── 2. Criar ad PAUSED em cada adset ──────────────────────────────────────────
print('\n2. Criando ads (PAUSED) em cada adset...')

asset_feed_spec = {
    'images': [{'hash': image_hash}],
    'bodies': [{'text': b} for b in BODIES],
    'titles': [{'text': t} for t in TITLES],
    'call_to_action_types': ['SHOP_NOW'],
    'link_urls': [{'website_url': LINK_URL}],
    'descriptions': [{'text': ''}],
    'ad_formats': ['AUTOMATIC_FORMAT'],
    'optimization_type': 'REGULAR',
}

creative_spec = {
    'name': f'bilheteria-presencial-{stem}',
    'object_story_spec': {'page_id': page_id},
    'asset_feed_spec': asset_feed_spec,
    'use_dynamic_creative': False,
}

results = []
for adset in ADSETS:
    ad_name = f'[{adset["prefix"]}] 3aEtapa bilheteria | {stem}'
    payload = {
        'name': ad_name,
        'adset_id': adset['id'],
        'status': 'PAUSED',
        'creative': json.dumps(creative_spec),
        'access_token': token,
    }
    data = urllib.parse.urlencode(payload).encode()
    create_url = f'https://graph.facebook.com/v25.0/{ad_account}/ads'
    req2 = urllib.request.Request(create_url, data=data, method='POST')
    try:
        resp2 = urllib.request.urlopen(req2)
        r = json.loads(resp2.read())
        ad_id = r.get('id')
        print(f'   OK  [{adset["prefix"]}] {adset["name"][:40]} → ad_id={ad_id}')
        results.append({'adset': adset['name'], 'ad_id': ad_id, 'status': 'PAUSED'})
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        print(f'   ERR [{adset["prefix"]}] {adset["name"][:40]} → {err.get("error", {}).get("message")}')
        print(f'       subcode={err.get("error", {}).get("error_subcode")}')
        results.append({'adset': adset['name'], 'error': err})

print('\n── RESUMO ──────────────────────────────────────────────────')
for r in results:
    if 'ad_id' in r:
        print(f'  PAUSED  {r["adset"][:45]} → {r["ad_id"]}')
    else:
        print(f'  FALHOU  {r["adset"][:45]}')
print('\nTodos os ads estão PAUSED. Renato revisa e ativa no Gerenciador.')
